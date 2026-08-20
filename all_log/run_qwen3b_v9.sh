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
[ "$n_cut" -lt 1000 ] && { echo "★ 중단: cut 이 너무 적다($n_cut)" | tee -a "$LOG"; exit 1; }

# ── 사전점검 3: 예제 캐시 ──
# ★★ **캐시를 지우지 마라.**
#   ExampleCache 는 캐시 미스 때 그 파일의 예제를 **전부**(모든 proof × step) 만들어
#   pickle 로 저장한다. 파일 하나에 600쌍이면 한 번에 600개 예제 분량의 검색이다
#   (실측: step 하나가 376초). 지우면 그 비용을 처음부터 다시 낸다.
#   실측 워밍 속도 약 19.5 파일/분 · 전체 13,896 파일 → 약 12시간.
#   캐시가 차면 검색이 사라지고 pickle 읽기만 남아 GPU 바운드가 된다.
#
#   설정을 바꿨을 때만 지운다. 그 판단은 CACHE_STAMP.txt 가 대신 해 준다 —
#   검색에 영향을 주는 설정이 달라지면 학습이 **큰 소리로 멈춘다**(조용히 섞이지 않게).
CACHE_LOC=$(python3 -c "import yaml;print(yaml.safe_load(open('$CONF'))['tactic_data']['cache_loc'])")
if [ -d "$CACHE_LOC" ]; then
  echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')]   예제 캐시: $(ls "$CACHE_LOC" | wc -l) 파일 · $(du -sh "$CACHE_LOC" 2>/dev/null | cut -f1)" | tee -a "$LOG"
else
  echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')]   예제 캐시 없음 — 처음부터 워밍한다(약 12시간)" | tee -a "$LOG"
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
