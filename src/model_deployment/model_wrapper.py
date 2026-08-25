from __future__ import annotations
import rango_defaults as _D   # ★ 프로덕션 기본값 단일 출처
from typing import Any, Callable, Optional
from pathlib import Path
import yaml
import ipdb
import functools

import sys, os
import re
from enum import Enum

from transformers import (
    AutoTokenizer,
    PreTrainedTokenizer,
    PreTrainedModel,
    BitsAndBytesConfig,
)
import torch

from util.train_utils import get_required_arg

from tactic_gen.lm_example import (
    LmExample,
)
from tactic_gen.train_decoder import (
    TRAINING_CONF_NAME,
    load_config,
    get_tokenizer,
    get_model,
)
from tactic_gen.tactic_data import (
    ExampleCollator,
    ProofPremiseCollator,
    NoScriptCollator,
    example_collator_from_conf,
    example_collator_conf_from_yaml,
    NEWLINE_RESPONSE_TEMPLATE,
)
from model_deployment.model_result import ModelResult, filter_recs



_FENCE_RE = re.compile(r"^\s*```")
_SECTION_RE = re.compile(r"^\[[A-Z][A-Z_ -]*\]\s*$")


def _first_tactic(text: str) -> str:
    """생성문에서 **첫 Coq tactic 한 줄**만 추출(SFT 안 한 베이스 모델 zero-shot 평가용).

    실측(Qwen2.5-Coder-3B 원시출력 48건)을 보면 **첫 줄이 거의 항상 tactic**이고
    그 뒤에 [END] / 코드펜스 / 영어 해설이 따라붙는다:

        "auto.⏎[END]⏎The lemma `is_nan_SF2FF` has been proved using ..."
        "auto with typeclass_instances⏎```⏎The tactic `auto with ...` will ..."

    그래서 위에서부터 훑으며 **처음 나오는 tactic 같은 줄**을 돌려준다.
    (예전엔 코드펜스를 우선 처리해서, 뒤쪽 펜스 안의 해설을 tactic 으로 잘못 집었다.)
    걸러야 하는 것: 영어 산문 · 선언문/명제(모델이 [PREMISES]·[STATE] 를 베껴 씀) · 섹션 헤더.
    못 찾으면 원문 그대로 — Coq 가 INVALID 로 판정(실패 집계가 맞다).
    """
    if not text or not text.strip():
        return text

    def _clean(ln: str) -> str:
        m = re.match(r"^(.*?\.)(\s|$)", ln)
        ln = (m.group(1) if m else ln).strip()
        return ln if ln.endswith((".", ";")) else ln + "."

    for raw in text.split("\n"):
        ln = raw.strip()
        if not ln or ln.startswith("```") or _SECTION_RE.match(ln):
            continue
        if ln.startswith("(*") or ln.startswith("*"):
            continue
        if ln.rstrip(".") + "." in _TERMINALS:
            return ln.rstrip(".") + "."
        if _is_prose(ln) or _is_decl(ln):
            continue
        # tactic 은 소문자로 시작하거나 불릿(-+*)/중괄호/대괄호로 시작한다
        if not re.match(r"^[a-z_]|^[-+*{}\[]", ln):
            continue
        # 명제를 그대로 베낀 줄 거부 — 단 명제를 인자로 받는 tactic 은 예외
        if ("->" in ln or " = " in ln) and not re.match(
                r"^(replace|assert|cut|change|pose|set|remember|specialize|enough|"
                r"refine|exact|apply|eapply|rewrite|erewrite|generalize|destruct)\b", ln):
            continue
        return _clean(ln)
    return text


_TERMINALS = {"Proof.", "Qed.", "Defined.", "Admitted.", "Abort."}


# 선언문 판별: 모델이 [PREMISES] 블록을 그대로 베껴 쓰는 일이 잦다(실측:
#   "Eval_get : forall (F V: Type) (genv: Genv.t F V) ..." 를 tactic 으로 뱉음).
#   `이름 : 타입` 꼴이나 Lemma/Theorem 머리는 tactic 이 아니다.
_DECL_RE = re.compile(
    r"^(Lemma|Theorem|Definition|Corollary|Remark|Fact|Inductive|Fixpoint|Variable|"
    r"Hypothesis|Axiom|Record|Notation|Require|Import|Section|Context)\b"
    r"|^[A-Za-z_][\w'.]*\s*:\s*(forall|\S)")


def _is_decl(ln: str) -> bool:
    return bool(_DECL_RE.match(ln))


# 산문 판별: 흔한 영어 기능어가 섞여 있고 단어가 많으면 tactic 이 아니다.
_PROSE_W = re.compile(
    r"\b(the|this|that|we|is|are|and|of|to|in|with|for|it|which|has|been|will|"
    r"defines|proves|uses|script|theorem|proof|following|here|lemma|code|tactic)\b", re.I)


def _is_prose(ln: str) -> bool:
    words = ln.split()
    return len(words) > 6 and len(_PROSE_W.findall(ln)) >= 2


class TokenMask(Enum):
    STATE = 0
    SCRIPT = 1
    PROOF = 2
    PREMISE = 3

    @classmethod
    def from_str(cls, s: str) -> TokenMask:
        match s:
            case "state":
                return cls.STATE
            case "script":
                return cls.SCRIPT
            case "proof":
                return cls.PROOF
            case "premise":
                return cls.PREMISE
            case _:
                raise ValueError(f"Invalid token mask: {s}")


def find_id_start_idx(t: torch.Tensor, s: torch.Tensor) -> Optional[int]:
    for i in range(t.shape[0] - s.shape[0] + 1):
        if torch.all(t[i : i + s.shape[0]] == s):
            return i
    return None


def get_enclosing_seps(
    collator: ExampleCollator, token_mask: TokenMask
) -> tuple[str, str]:
    match collator:
        case ProofPremiseCollator():
            match token_mask:
                case TokenMask.STATE:
                    return (collator.STATE_SEP, collator.SCRIPT_SEP)
                case TokenMask.SCRIPT:
                    return (collator.SCRIPT_SEP, NEWLINE_RESPONSE_TEMPLATE)
                case TokenMask.PROOF:
                    return (collator.PROOF_SEP, collator.STATE_SEP)
                case TokenMask.PREMISE:
                    return (collator.PREMISE_SEP, collator.PROOF_SEP)

        case NoScriptCollator():
            match token_mask:
                case TokenMask.STATE:
                    return (collator.STATE_SEP, NEWLINE_RESPONSE_TEMPLATE)
                case TokenMask.SCRIPT:
                    raise ValueError(
                        "NoScriptCollator does not support SCRIPT token masking."
                    )
                case TokenMask.PROOF:
                    return (collator.PROOF_SEP, collator.STATE_SEP)
                case TokenMask.PREMISE:
                    return (collator.PREMISE_SEP, collator.PROOF_SEP)

        case _:
            raise ValueError(f"Token masking not supported for {collator}.")


def transform_attention_mask(
    collator: ExampleCollator,
    tokenizer: PreTrainedTokenizer,
    token_mask: Optional[TokenMask],
    input_ids: torch.Tensor,
    attn_mask: torch.Tensor,
) -> torch.Tensor:
    if token_mask is None:
        return attn_mask
    start_str, end_str = get_enclosing_seps(collator, token_mask)
    start_ids = tokenizer.encode(start_str, add_special_tokens=False)
    end_ids = tokenizer.encode(end_str, add_special_tokens=False)

    changed_mask = attn_mask.clone()
    for i, id_row in enumerate(input_ids):
        start_idx = find_id_start_idx(id_row, torch.tensor(start_ids))
        end_idx = find_id_start_idx(id_row, torch.tensor(end_ids))
        assert start_idx is not None
        assert end_idx is not None
        changed_mask[i, start_idx:end_idx] = 0
    return changed_mask


class DecoderLocalWrapper:
    ALIAS = "decoder-local"

    def __init__(
        self,
        model: PreTrainedModel,
        tokenizer: PreTrainedTokenizer,
        collator: ExampleCollator,
        hard_seq_len: int,
        normalize_inference: Optional[bool] = None,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.collator = collator
        self.hard_seq_len = hard_seq_len
        # ★★ **추론 프롬프트 정규화는 여기서만 켠다.**
        #   전역 env 로 두면 학습 경로로 샌다 — `collate`(학습)가 내부에서
        #   `collate_input` 을 부르기 때문이다. 실제로 그렇게 새서 프롬프트는
        #   `Lemma L##`, 정답은 `ltu_inv` 로 어긋난 채 학습됐다(CompCert 결손 27→99).
        #   그래서 **파이썬 인자**로 받고, 이 값만 collator 에 명시적으로 넘긴다.
        #   env 는 인자를 안 준 경우의 기본값으로만 쓴다(추론 프로세스 안에서만 읽힌다).
        #   기본값은 **켬**이다(모델이 익명 이름으로 학습되므로). 끄려면 명시로
        #   normalize_inference=False 를 주거나 NORMALIZE_INFERENCE=0 을 준다.
        self.normalize_inference = (
            bool(normalize_inference) if normalize_inference is not None
            else _D.flag("NORMALIZE_INFERENCE"))

    def get_recs(
        self,
        example: LmExample,
        n: int,
        current_proof: str,
        beam: bool,
        token_mask_str,
    ) -> ModelResult:
        token_mask = None
        if token_mask_str is not None:
            token_mask = TokenMask.from_str(token_mask_str)
        collated_input = self.collator.collate_input(
            self.tokenizer, example, normalize=self.normalize_inference)
        inputs = self.tokenizer(
            collated_input,
            max_length=self.hard_seq_len,
            truncation=True,
            return_tensors="pt",
        )
        attention_mask = transform_attention_mask(
            self.collator,
            self.tokenizer,
            token_mask,
            inputs["input_ids"],
            inputs["attention_mask"],
        )
        use_beam = beam and 1 < n
        generate_kwargs = dict(
            # ★ 정답 자리. cut 의 `assert (P) as H_asrt0.` 는 명제 전체를 쓰므로
            #   보통 tactic(중앙 4토큰)보다 훨씬 길다. 상한을 올리는 비용은 **0** 이다
            #   — 생성은 EOS 에서 멈추므로 실제로 그만큼 뽑을 때만 시간이 든다
            #   (실측: 생성 ≈ 354ms + 16.1ms × 실제 출력토큰, 3B·n=8).
            max_new_tokens=_D.num("OUT_TOKENS"),
            return_dict_in_generate=True,
            output_scores=True,
            num_return_sequences=n,
            attention_mask=attention_mask.cuda(),
        )
        if use_beam:
            generate_kwargs["num_beams"] = n
            generate_kwargs["length_penalty"] = 0
        else:
            generate_kwargs["do_sample"] = True
            generate_kwargs["temperature"] = 1.0
            generate_kwargs["num_beams"] = 1
        with torch.no_grad():
            outputs = self.model.generate(
                inputs["input_ids"].cuda(),
                **generate_kwargs,
            )
        input_num_tokens = inputs["input_ids"].shape[1]
        generated_seqs = outputs.sequences[:, input_num_tokens:]
        tactics = self.tokenizer.batch_decode(generated_seqs, skip_special_tokens=True)
        # ★ 추론 정규화를 켰다면 **반드시 되돌린다.** 모델은 프롬프트에서 본 `L0` 를
        #   그대로 생성하는데 Coq 은 `L0` 를 모른다. 매핑에 없는 이름(모델이 지어낸 것)은
        #   그대로 둔다 — Coq 에서 실패하는 것이 맞다. 조용히 바꾸면 환각을 숨기게 된다.
        if self.normalize_inference:
            from tactic_gen.tactic_data import last_inference_mapping
            from tactic_gen.normalize_names import apply_inverse
            _m = last_inference_mapping()
            if _m:
                tactics = [apply_inverse(t, _m) for t in tactics]

        # ★ 절제 실험용 — `assert` 후보를 버린다 (`NO_ASSERT=1`, 기본 꺼짐).
        #   `CUT_SUBSTEP` 은 **학습 데이터** 경로에만 있어(tactic_data.py) 추론엔 영향이 없다.
        #   모델은 이미 cut 패턴을 배웠으므로, 추론에서 끄려면 후보를 걸러야 한다.
        #   실측 근거(rand200 200정리):
        #     · 고유 assert 명제 3,486개 중 gold lemma 재구성은 2.0% 뿐, 81.6%는 근거 없는 명제
        #     · assert 를 시도한 정리 성공률 17.3% vs 안 쓴 정리 59.0%
        #       (다만 어려운 정리에서만 꺼내므로 인과는 불확실 — 그래서 이 절제를 만든다)
        #     · 반대로 성공 60개 중 5개는 assert 로 풀었다(설계대로의 3단 체인)
        if os.environ.get("NO_ASSERT", "0") == "1":
            import re as _re
            _keep = [t for t in tactics if not _re.match(r"\s*e?assert\b", t)]
            if _keep:
                tactics = _keep

        # ★★ 기본값을 **학습 설정에서 유도**한다 — 별도 env 로 두면 잊는다(실제로 잊었다).
        #   학습이 정답의 선행 개행을 떼면(`STRIP_TARGET_NL=1`, 지금 프로덕션 기본값)
        #   모델은 개행 없이 뱉는다. 그러면 탐색기가 `script + tactic` 으로 이어붙일 때
        #   `Theorem X : stmt.` + `Proof.` → `stmt.Proof` 가 되어 Coq 이 **한정이름**으로
        #   읽는다 → "Syntax error: '.' expected after [gallina]".
        #   실측: 이 한 줄이 빠져 rand200 한 정리가 600초 동안 같은 오류를 1,387번 냈다.
        #   두 설정은 **논리적으로 같은 하나의 사실**이므로 따로 두면 안 된다.
        #   (명시 env 는 여전히 이긴다 — 절제 실험용.)
        _lead = os.environ.get("TACTIC_LEADING_NL")
        if _lead == "1" or (_lead is None and _D.flag("STRIP_TARGET_NL")):
            # STRIP_TARGET_NL=1 로 학습한 모델(Qwen 계열)은 선행 개행 없이 tactic 을 뱉는다.
            # 탐색기는 cur_proof_script + tactic 으로 이어붙이므로 개행이 없으면
            # "...end.Proof." 처럼 붙어 Coq 이 한정이름으로 파싱한다 → 반드시 복원한다.
            tactics = [t if t.startswith("\n") else "\n" + t for t in tactics]
        if os.environ.get("ZEROSHOT_CLEAN", "0") == "1":
            # SFT 안 한 베이스 모델은 tactic 한 줄이 아니라 **증명 전체·설명·마크다운**을 뱉는다.
            # (실측: 3B가 "```coq\nauto\n```\nThis script defines the theorem ..." 형태)
            # 그대로 Coq 에 넣으면 전부 구문오류 INVALID 라 모델 간 비교가 성립하지 않는다.
            # → 첫 tactic 한 줄만 잘라낸다. SFT 모델에는 이 env 를 켜지 않으므로 영향 없음.
            tactics = [_first_tactic(t) for t in tactics]
        non_special_tokens = torch.concat(
            [(generated_seqs != t)[:, :, None] for t in self.tokenizer.all_special_ids],
            axis=2,
        ).all(dim=2)
        lengths = non_special_tokens.sum(axis=1).tolist()
        if beam and 1 < n:
            scores = outputs.sequences_scores.tolist()
            return ModelResult(tactics, scores, lengths)
        else:
            with torch.no_grad():
                transition_scores = self.model.compute_transition_scores(
                    generated_seqs, outputs.scores, normalize_logits=True
                )
                scores = (
                    transition_scores.where(
                        transition_scores != -torch.inf, torch.tensor(0.0)
                    )
                    .sum(axis=1)
                    .tolist()
                )
                return ModelResult(tactics, scores, lengths)

    def generate_raw(
        self,
        prompt: str,
        n: int = 8,
        max_new_tokens: int = 256,
        temperature: float = 1.0,
    ) -> list[str]:
        """자유형(free-form) 생성. collator/next-tactic 포맷을 우회하고 prompt를 그대로
        토크나이즈해 샘플링한다. Quarry 분해 생성(=[LEMMA]/[TARGET] 블록)에 사용."""
        inputs = self.tokenizer(
            prompt,
            max_length=self.hard_seq_len,
            truncation=True,
            return_tensors="pt",
        )
        generate_kwargs = dict(
            max_new_tokens=max_new_tokens,
            do_sample=temperature > 0,
            num_return_sequences=n,
            num_beams=1,
            attention_mask=inputs["attention_mask"].cuda(),
            pad_token_id=self.tokenizer.eos_token_id,
        )
        if temperature > 0:
            generate_kwargs["temperature"] = temperature
        with torch.no_grad():
            outputs = self.model.generate(
                inputs["input_ids"].cuda(),
                **generate_kwargs,
            )
        input_num_tokens = inputs["input_ids"].shape[1]
        generated_seqs = outputs[:, input_num_tokens:]
        return self.tokenizer.batch_decode(generated_seqs, skip_special_tokens=True)

    @classmethod
    def get_training_conf(cls, checkpoint_loc: Path) -> Any:
        training_conf_loc = checkpoint_loc.parent / TRAINING_CONF_NAME
        with training_conf_loc.open("r") as f:
            training_conf = yaml.safe_load(f)
        return training_conf

    @classmethod
    def from_checkpoint(cls, checkpoint_loc: Path,
                        normalize_inference: Optional[bool] = None) -> DecoderLocalWrapper:
        """`normalize_inference` — 추론 프롬프트를 학습과 같은 형태로 익명화할지.

        ★ **명시 인자로 받는다.** 전역 env 로 두면 학습 경로로 샌다(`collate` 가
          내부에서 `collate_input` 을 부른다). None 이면 학습 설정에서 읽고,
          그것도 없으면 env 를 본다 — env 는 추론 프로세스 안에서만 읽힌다.
        """
        training_conf = cls.get_training_conf(checkpoint_loc)
        if normalize_inference is None and "normalize_inference" in training_conf:
            # 체크포인트의 학습 설정이 명시하면 그것을 따른다(사람이 잊는 사고 방지).
            normalize_inference = bool(training_conf["normalize_inference"])
        hard_seq_length = get_required_arg("hard_seq_len", training_conf)
        example_collator_conf = example_collator_conf_from_yaml(
            training_conf["example_collator"]
        )
        # ★★ **체크포인트의 학습 설정을 이 프로세스의 단일 출처로 만든다.**
        #
        #   래퍼는 여기서 읽은 `hard_seq_len` 으로 자르는데, 프롬프트를 만드는
        #   collator 쪽(`tactic_data`)은 `rango_defaults` 를 본다. 둘이 다르면
        #   **정규화가 깨진다**:
        #     정규화는 "프롬프트에 실제로 실리고 **절단 후에도 보이는**" premise 만
        #     대상으로 삼는다(`_vis`). 그 창이 실제 절단(2048)보다 넓으면(3072),
        #     잘려나갈 premise 에까지 `_L#` 을 배정한다 → 모델은 프롬프트 어디에도
        #     없는 `_L7` 을 보게 되고, 그건 정확히 우리가 없애려던 환각이다.
        #   그리고 `room = hard − base − out_tokens − margin` 도 같은 값을 써야
        #   주입량이 학습과 같아진다.
        #
        #   env 가 **명시적으로** 주어졌으면 그것을 존중한다(절제 실험용).
        #   추론 프로세스 안에서만 설정하므로 학습 경로로 새지 않는다.
        for _k, _v in (("HARD_SEQ_LEN", hard_seq_length),
                       ("OUT_TOKENS", training_conf["example_collator"].get("out_tokens"))):
            if _v and not os.environ.get(_k):
                os.environ[_k] = str(_v)
        example_collator = example_collator_from_conf(example_collator_conf)
        tokenizer = get_tokenizer(
            get_required_arg("model_name", training_conf), add_eos=False
        )
        # ★ SFT 없는 베이스 모델 평가: 체크포인트 디렉토리에 가중치가 없으면
        #   training_conf 의 model_name(HF 이름)을 그대로 로드한다.
        #   (models/nosft-* 처럼 conf 만 두고 베이스 성능을 재는 용도)
        _has_w = any(checkpoint_loc.glob("*.safetensors")) or \
            (checkpoint_loc / "adapter_config.json").exists() or \
            (checkpoint_loc / "pytorch_model.bin").exists()
        _src = str(checkpoint_loc.resolve()) if _has_w else \
            get_required_arg("model_name", training_conf)
        model = get_model(_src, load_in_4bit=bool(training_conf.get("load_in_4bit", True)))
        # ★ bf16 경로(load_in_4bit=false)는 device_map 없이 CPU 에 올라온다 → 직접 GPU 로.
        #   (4bit 경로는 BitsAndBytes 가 device_map 으로 이미 올림)
        try:
            import torch as _torch
            if _torch.cuda.is_available() and next(model.parameters()).device.type == "cpu":
                model = model.cuda()
        except StopIteration:
            pass
        return cls(model, tokenizer, example_collator, hard_seq_length,
                   normalize_inference=normalize_inference)

    @classmethod
    def from_conf(cls, json_data: Any) -> DecoderLocalWrapper:
        name = json_data["checkpoint_loc"]
        # 평가 설정에서 명시로 줄 수 있다: {"normalize_inference": true}
        return cls.from_checkpoint(Path(name),
                                   normalize_inference=json_data.get("normalize_inference"))


class StubWrapper:
    def get_recs(
        self,
        example: LmExample,
        n: int,
        current_proof: str,
        beam: bool,
        token_mask: Optional[str],
    ) -> ModelResult:
        return ModelResult([], [], [])

    def generate_raw(
        self,
        prompt: str,
        n: int = 8,
        max_new_tokens: int = 256,
        temperature: float = 1.0,
    ) -> list[str]:
        return []


ModelWrapper = DecoderLocalWrapper | StubWrapper


class WrapperNotFoundError(Exception):
    pass


def wrapper_from_conf(conf: Any) -> ModelWrapper:
    attempted_alias = conf["alias"]
    match attempted_alias:
        case DecoderLocalWrapper.ALIAS:
            return DecoderLocalWrapper.from_conf(conf)
        case _:
            raise WrapperNotFoundError(
                f"Could not find model wrapper: {attempted_alias}"
            )
