#!/bin/bash
# v9 = v8 에서 **검색 파이프라인만** 바꾼 재학습. conf(하이퍼파라미터)는 v8 과 동일하다.
#      바뀐 것은 전부 환경변수 4줄이고, 근거는 all_log/docs/premise/final.md §10 에 있다.
#
#  ① RETRIEVAL_MODE=structural   (기존: tfidf)
#     근거: 목표지표 A+(1-A)×C · 프롬프트기준 ALL
#           TRAIN 80.5→95.6 · TEST 80.3→95.3 · VAL 79.7→96.5
#           ※ 두 수 모두 cut 포함. cut 없는 v8 원본의 A 는 TEST 27.7% 였다.
#
#  ② PREMISE_PACK=hybrid TOPK=4  (기존: greedy — 안 들어가면 거기서 멈춤)
#     근거: 상위 4개는 무조건 넣고 나머지는 배낭(가치÷무게)으로 채운다.
#           gold 포함률 TRAIN -0.9p / TEST +9.0p / VAL +15.4p (평균 +7.8p).
#           긴 premise 하나가 짧은 것 여러 개를 밀어내던 문제를 없앤다.
#
#  ③ CUTS_PATH=data/cuts_train.jsonl
#     근거: gold lemma 가 프롬프트에 없으면(=모델이 볼 수 없으면) 그 이름을 외우게 하는 것은
#           환각을 가르치는 것이다. 대신 `assert (P) as H_asrtN. { exact L. }` 로 **명제를 세우고**
#           그 다음 스텝에서 쓰게 한다(cut rule). 명제를 세우면 그게 곧 goal 이라
#           재검색에서 최상위로 와 예산 안에 확실히 들어간다.
#           TRAIN 판정: ① 검색성공 4,973 / ② cut 5,278 / ③ 가망없음 3,852
#
#  ④ NORMALIZE_SKIP_STDLIB=1 INJECT_SKIP_STDLIB=1
#     근거: stdlib 이름(Nat.add_comm 등)은 어차피 import 로 들어오니 익명화 대상이 아니다.
#           ★ 다만 **환각률은 안 줄었다**(익명화 OFF 7.9% vs ON 8.0%). 프로브로 확인한 바
#           모델은 stdlib lemma 의 명제를 모른다(F1 0.292 vs 가짜이름 대조군 0.291).
#           그래서 stdlib 도 ①②③ 판정을 똑같이 거친다. 이 플래그는 **무해하지만 이득도 없다.**
#
#  ★ ③ 가망없음(hopeless) 스텝은 **정규화를 끈다.**
#     정답이 프롬프트에 없는 이름을 쓰는데 정규화까지 하면 `L92` 같은 무의미 토큰을 외운다.
#     진짜 이름이 그나마 낫다.
#
#  유지: 베이스 Qwen2.5-Coder-3B-Instruct · lr 1e-4 cosine/20k · hard_seq_len 2048
#        NORMALIZE_NAMES=1 RATE=0.5 · func_defs_v3.json · save/eval 1000
#  ★ 엔트리를 train_v5.py 로 두는 이유는 v8 주석 참조(다른 세션의 프로세스 일괄종료 회피).
cd /app/coq-modeling || exit 1
set -u
CONF=all_log/ft_qwen3b_v9_conf.yaml
LOG=all_log/ft_qwen3b_v9.log
OUT=models/rango-qwen3b-v9-ft
NPROC=${NPROC:-2}

mkconf_resume(){
  local best="" d p
  for d in $(ls -d "$OUT"/checkpoint-* 2>/dev/null | sed 's/.*checkpoint-//' | sort -rn); do
    p="$OUT/checkpoint-$d"
    if [ -f "$p/trainer_state.json" ] && ls "$p"/*.safetensors >/dev/null 2>&1; then best="$p"; break; fi
    echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')]   ★ 손상 체크포인트 격리: $p" >> "$LOG"
    mv "$p" "$OUT/broken-checkpoint-$d" 2>/dev/null
  done
  if [ -n "$best" ]; then
    python3 - "$CONF" "$best" <<'PYX' 2>/dev/null
import sys, yaml
c = yaml.safe_load(open(sys.argv[1])); c["checkpoint_name"] = sys.argv[2]
open("/tmp/ft_qwen3b_v9_resume.yaml", "w").write(yaml.safe_dump(c, allow_unicode=True))
PYX
    echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')]   재개 지점: $best" >> "$LOG"
    echo "/tmp/ft_qwen3b_v9_resume.yaml"
  else
    echo "$CONF"
  fi
}

# ── 사전점검 1: /tmp 스테이징 무결성 (v8 과 동일) ──
SRC=data/coq-dataset
DST=$(python3 -c "import yaml;print(yaml.safe_load(open('$CONF'))['tactic_data']['data_loc'])")
if [ "$DST" != "$SRC" ]; then
  n_src=$(ls "$SRC/data_points" 2>/dev/null | wc -l)
  n_dst=$(ls "$DST/data_points" 2>/dev/null | wc -l)
  if [ "$n_src" != "$n_dst" ]; then
    echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')]   ★ 스테이징 불일치 ($n_dst/$n_src) — 재복사" | tee -a "$LOG"
    mkdir -p "$DST" && rsync -a "$SRC/" "$DST/"
    echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')]   재복사 완료 ($(ls "$DST/data_points" | wc -l)/$n_src)" | tee -a "$LOG"
  fi
fi

# ── 사전점검 2: cut 파일 ──
# ★ cut 파일이 없거나 0바이트면 조용히 비활성화되어 v8 과 똑같은 학습이 된다.
#   그러면 "돌려봤는데 v8 과 같더라" 는 결론을 얻고 원인을 못 찾는다. 여기서 막는다.
CUTS=data/cuts_train.jsonl
if [ ! -s "$CUTS" ]; then
  echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] ★ 중단: $CUTS 가 없거나 비었다" | tee -a "$LOG"; exit 1
fi
n_cut=$(grep -c '"cut"' "$CUTS")
echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')]   cut 파일 확인: $(wc -l < "$CUTS") 줄 · cut $n_cut 개" | tee -a "$LOG"

# ★★ 개수가 아니라 **커버리지**를 본다.
#   예전 가드는 `n_cut -lt 1000` 이었다. cut 4,648개로 통과했지만 실제로는
#   학습이 소비하는 640,000 예제 중 **처음 60,000(9.4%)** 만 덮고 있었다.
#   build_cuts.py 가 파일럿 규모로 돌아간 산출물이 그대로 들어간 것이다.
#   step 1,875 이후로 cut 치환도 CUT_DROP_HOPELESS 도 전혀 작동하지 않았다.
#   (is_hopeless() 는 파일에 없는 스텝에 False 를 반환하므로 둘이 함께 죽는다)
#   → 학습이 실제로 쓰는 인덱스 구간을 표본으로 찍어 적중률을 확인한다.
# ★★ 커버리지를 **표본이 아니라 전수로** 검증한다.
#   개수 가드(`n_cut -lt 1000`)로는 파일럿 산출물을 못 걸렀다 — cut 4,648개로 통과했지만
#   실제로는 소비 640,000 중 처음 60,000(9.4%)만 덮고 있었다.
#   그리고 표본 5곳만 찍었을 때도 640,000 이후 빈틈을 놓쳤다
#   (CUT_DROP_HOPELESS 가 인덱스를 건너뛰어 도달 인덱스가 671,835 였다).
#   → verify_cut_range.py 가 도달 인덱스를 **시뮬레이션**하고 전 구간을 훑는다.
if ! PYTHONPATH=src python3 scripts/verify_cut_range.py "$CONF" "$CUTS" 2>&1 | tee -a "$LOG" | tail -20; then
  echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] ★ 중단: cut 범위 검증 실패" | tee -a "$LOG"
  exit 1
fi
if ! PYTHONPATH=src python3 scripts/verify_cut_range.py "$CONF" "$CUTS" > /dev/null 2>&1; then
  echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] ★ 중단: cut 범위 검증 실패 (위 로그 참조)" | tee -a "$LOG"
  exit 1
fi

USE=$(mkconf_resume | tail -1)
echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] ===== v9 학습 시작 (Qwen3B, ${NPROC}GPU, conf=$(basename "$USE")) =====" | tee -a "$LOG"
# ★ 환경변수는 all_log/v9_env.sh 한 곳에만 둔다 — 검증 스크립트도 같은 파일을 쓴다.
#   두 곳에 나열하면 "검증한 설정 != 학습한 설정" 이 되고, 그건 조용히 어긋난다.
source all_log/v9_env.sh
export CUTS_PATH="$CUTS"
  python3 -m torch.distributed.run --nproc_per_node="$NPROC" --master_port=$((29500 + RANDOM % 400)) \
    src/tactic_gen/train_v5.py "$USE" >> "$LOG" 2>&1
echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] ===== v9 종료(rc=$?) =====" | tee -a "$LOG"
