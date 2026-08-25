# `apply` · `rewrite` — 형태와, 그 형태를 내는 데 필요한 정보

한 주제를 앞뒤로 나눠 본 두 문서다.

| 문서 | 무엇 |
|---|---|
| [apply-rewrite-forms.md](apply-rewrite-forms.md) | **증상.** `apply`·`rewrite` 가 취할 수 있는 형태를 문법으로 전부 세우고, CompCert 실측(45,572회)과 모델 실측(15,453 생성) 분포를 나란히 둔다 |
| [apply-automation-gap.md](apply-automation-gap.md) | **원인.** `apply` 가 내부적으로 하는 다섯 단계 중 프롬프트가 받쳐 주는 것과 아닌 것. CompCert 실제 스텝 하나를 끝까지 따라간다 |

## 둘이 어떻게 이어지나

`apply-rewrite-forms.md` §4-④ 는 위치 인자형이 오히려 나쁘다는 것을 잰다 —
`apply (L a _ c)` 42.9% · `apply L a b` 44.1% 로 맨 `apply`(17.1%)보다 나쁘고,
이유를 "**arity 와 순서를 모르기 때문**"으로 짚는다.

`apply-automation-gap.md` 는 **왜 모를 수밖에 없는지**를 짚는다 — premise 가 소스
선언문 그대로 실리므로 섹션 변수 방출 · `Set Implicit Arguments` · `Arguments` 가
반영된 **진짜 arity 가 프롬프트에 없다**(선언의 11.3%, 하한). 모르는 게 아니라
**읽을 수 없다.**

그래서 처방도 두 층이다.

- 형태 층 — 변형 집합에서 위치 인자형을 빼고 `with (x := e)` · `eapply` · `rewrite (L a b)`
  같은 *arity 를 몰라도 되는 부분 지정* 으로 잡는다 (`apply-rewrite-forms.md` §5)
- 정보 층 — 모듈 경로 · 펑터 전개 · 섹션 변수 방출을 premise 문장에 되돌린다
  (`apply-automation-gap.md` §9)

## 딸린 원본

| 파일 | 무엇 |
|---|---|
| `example-prompt.txt` | `apply-automation-gap.md` 가 다루는 스텝의 v9 추론 프롬프트 전문 (2,003토큰) |
| `example-mapping.json` | 그 프롬프트의 익명화 매핑 (실명 → `_L#`/`_f#`/`_T#`/`_C#`/`_G#`) |

재현:

```bash
PYTHONPATH=src python3 scripts/dump_one_prompt.py \
    /tmp/coq-dataset/data_points/AbsInt-CompCert-backend-Unusedglobproof.v 52 5 \
    all_log/docs/v9/apply
```

## 관련 문서

- `all_log/docs/premise/functor-names.md` — 펑터가 만든 이름이 검색 풀에 없는 문제
- `all_log/docs/premise/final.md` — 랭커(afh70) 설계와 실측
- `all_log/docs/premise/normalize.md` — 이름 익명화
- `all_log/docs/dpo-design.md` — 형태 쌍(Tier A) DPO 설계
- `prompt_examples_comparison/v9_vs_rango/` — rango 원본 프롬프트와의 40건 나란히 비교
