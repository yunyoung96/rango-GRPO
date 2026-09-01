#!/usr/bin/env python3
"""★★ **TRAIN 풀 수집기** — 가중치 전이 실험의 반쪽.

지금까지 가중치는 VAL 안에서 leave-one-out 으로 학습·평가했다. 리뷰어는
"실사용에선 학습 스플릿에서 굳힌 가중치를 새 프로젝트에 그대로 써야 한다"
고 물을 것이다. 그 조건을 만들려면 **TRAIN 지점**이 필요하다.

TRAIN 은 CoqStoq 저장소가 아니라 `raw-data/coq-dataset/data_points` 다.
    · dp 파일명 = `owner-repo-경로.v` (하이픈 경계 모호 → dp 안의
      `file_context.file` 로 원경로를 되찾는다)
    · 정리 위치 = 저장소 파일에서 정리 진술문 **텍스트 검색**
      (커밋을 `splits/commits.json` 으로 맞춰 클론했으므로 어긋나면 건너뜀)
    · 나머지 재생·필터·기록은 r11_eval.run 을 **그대로** 쓴다 —
      두 벌 만들면 반드시 어긋난다.

사용: python3 scripts/train_pool.py [프로젝트당_정리수] [저장소들]
      저장소 = `이름=경로,이름=경로`  (기본: coq-art)
"""
import collections, concurrent.futures as cf, json, os, re, sys, logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "scripts"); sys.path.insert(0, "CoqStoq")
logging.disable(logging.CRITICAL)
from pathlib import Path

# ★ r11_eval 은 모듈 상단에서 argv 를 읽는다 — import 전에 밀어 넣는다.
_ARGV = sys.argv[:]
sys.argv = ["r11_eval.py", "VAL", "0", "", ""]
import r11_eval as R
sys.argv = _ARGV

from data_management.sentence_db import SentenceDB
from data_management.dataset_file import DatasetFile

PER_PROJ = int(sys.argv[1]) if len(sys.argv) > 1 else 120
#: ★ only_in — `-in` 스텝 있는 정리만, 그 스텝 전부(≤6). 표본 보강용.
ONLY_IN = (sys.argv[3] if len(sys.argv) > 3 else "") == "only_in"
#: ★ all — ④ 전 지점 모드: 정리당 지점 상한 없음(SFT 물질화용). 출력 r11_pool_train_all.jsonl
ALL_PT = (sys.argv[3] if len(sys.argv) > 3 else "") == "all"
_SCR = "/app/coq-modeling/tmp/tr"   # 영속 위치 (scratchpad=tmpfs 는 세션 재시작 때 소실됨)
_DEF = f"coq-community-coq-art={_SCR}/coq-community-coq-art"
REPOS = dict(kv.split("=", 1) for kv in
             (sys.argv[2] if len(sys.argv) > 2 else _DEF).split(","))
DPD = "raw-data/coq-dataset/data_points"
OUT = ("all_log/r11_pool_train_onlyin.jsonl" if ONLY_IN
       else "all_log/r11_pool_train_all.jsonl" if ALL_PT
       else "all_log/r11_pool_train.jsonl")
JOBS = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else 2   # coqtop 워커 수 (12코어 공유 서버: 4 권장)
RESUME = "resume" in sys.argv[5:]   # 기존 출력의 (proj,thm,thmi) 는 건너뛰고 이어쓴다
MAX_PT = 10**9 if ALL_PT else 3
OTH_PER_THM = 5      # all 모드: 정리당 무참조 지점 상한 (균등 표본)

sdb = SentenceDB.load(Path("raw-data/coq-dataset/sentences.db"))

REPOS_NAME = {pd: nm for nm, pd in REPOS.items()}
for nm, pd in REPOS.items():
    assert os.path.isdir(pd), f"저장소 없음: {pd}"
    assert any(True for _ in Path(pd).rglob("*.vo")), f".vo 없음(빌드 안 됨): {pd}"


def dp_files(proj):
    """이 프로젝트의 dp 파일들. 파일명 접두사로 거른 뒤 원경로로 확정."""
    out = []
    for f in sorted(os.listdir(DPD)):
        if not f.startswith(proj + "-"): continue
        out.append(os.path.join(DPD, f))
    return out


def rel_of(dp, proj):
    """dp 안의 원경로 → 저장소 상대경로. `.../repos/<proj>/<rel>`"""
    fp = dp.file_context.file
    m = re.search(r"/repos/" + re.escape(proj) + r"/(.*)$", fp or "")
    return m.group(1) if m else None


def find_thm(orig, thm_text, start):
    """정리 진술문을 파일에서 찾는다 — 공백 정규화 검색.
    반환 = (문자 오프셋, 그 앞까지의 head). 못 찾으면 None."""
    first = " ".join(thm_text.split())
    # 원문에서 공백만 다른 경우를 잡기 위해 정규식으로 바꾼다
    pat = re.compile(r"\s+".join(re.escape(w) for w in first.split()[:8]))
    m = pat.search(orig, start)
    if not m: return None
    return m.start(), orig[:m.start()]


if __name__ == "__main__":
    jobs = []
    skip = collections.Counter()
    for proj, pdir in REPOS.items():
        got = 0
        for dpf in dp_files(proj):
            if got >= PER_PROJ: break
            try:
                dp = DatasetFile.load(Path(dpf), sdb)
            except Exception:
                skip["dp로드실패"] += 1; continue
            rel = rel_of(dp, proj)
            if not rel: skip["원경로실종"] += 1; continue
            path = os.path.join(pdir, rel)
            if not os.path.exists(path): skip["파일없음"] += 1; continue
            if not os.path.exists(os.path.splitext(path)[0] + ".vo"):
                skip["vo없음"] += 1; continue
            try:
                orig = open(path, errors="ignore").read()
            except Exception:
                skip["읽기실패"] += 1; continue
            pos = 0
            for pi, proof in enumerate(dp.proofs):
                if got >= PER_PROJ: break
                tt = proof.theorem.term.text or ""
                if not tt.strip(): continue
                hit = find_thm(orig, tt, pos)
                if hit is None:
                    skip["정리실종(드리프트)"] += 1; continue
                off, head = hit
                pos = off + 1          # 다음 정리는 이 뒤에서 찾는다 (동명 중복 대비)
                ks = [k for k, s in enumerate(proof.steps)
                      if R.HEADT.match(s.step.text or "")
                      and R.HEADT.match(s.step.text).group(1) in (
                          "apply", "eapply", "rewrite", "erewrite", "unfold",
                          "destruct", "induction", "case", "elim", "exact", "eexact")
                      and R.NAMED.search(s.step.text or "") and s.goals]
                ks_oth = []
                if ALL_PT:
                    # ★ all 모드: **무참조 스텝**(intros·simpl·constructor·split·auto…)도 지점으로 — SFT 는 증명의
                    #   모든 수를 배워야 한다(v10 도 전 스텝 학습). 외부참조 스텝은 전부, 무참조는 정리당 ≤ OTH_PER_THM 균등.
                    cand = [k for k, s in enumerate(proof.steps)
                            if k not in set(ks) and s.goals and R.HEADT.match(s.step.text or "")
                            and (s.step.text or "").strip() not in ("Proof.", "Qed.", "Defined.", "Admitted.")
                            and not re.match(r"^\s*[-+*{}]+\s*$", s.step.text or "")]
                    if cand:
                        stp = len(cand) / min(OTH_PER_THM, len(cand))
                        ks_oth = sorted({cand[int(i * stp)] for i in range(min(OTH_PER_THM, len(cand)))})
                if not ks and not ks_oth: continue
                if ONLY_IN:
                    ks = [k for k in ks
                          if R.tac_form(proof.steps[k].step.text or "")
                          in ("apply-in", "rewrite-in")][:6]
                    if not ks: continue
                ks_ext = list(ks)
                if len(ks) > MAX_PT and not ONLY_IN:
                    # ★ `-in` 을 먼저 챙긴다 — 전체의 2~6% 라 균등으론 안 모인다
                    _in = [k for k in ks if R.tac_form(proof.steps[k].step.text or "")
                           in ("apply-in", "rewrite-in")]
                    _rest = [k for k in ks if k not in set(_in)]
                    take = _in[:MAX_PT]
                    if len(take) < MAX_PT and _rest:
                        need = MAX_PT - len(take)
                        stp = len(_rest) / need
                        take += [_rest[int(x * stp)] for x in range(need)]
                    ks = sorted(set(take))
                ks = sorted(set(ks) | set(ks_oth))
                steps = [s.step.text for s in proof.steps]
                chunks, prev = {}, 0
                for k in ks: chunks[prev] = "".join(steps[prev:k]); prev = k
                golds = {k: (R.NAMED.search(proof.steps[k].step.text).group(1) if k in set(ks_ext) else None)
                         for k in ks}
                tacs = {}; texts = {}
                for _k in ks:
                    _t = proof.steps[_k].step.text or ""
                    texts[_k] = " ".join(_t.split())
                    tacs[_k] = R.tac_form(_t)
                jobs.append((pdir, path, head, tt, chunks, ks, golds,
                             tacs, texts, rel, pi))
                got += 1
    done_keys = set()
    if RESUME and os.path.exists(OUT):
        for l in open(OUT):
            try: r_ = json.loads(l); done_keys.add((r_["proj"], r_["thm"], r_["thmi"]))
            except Exception: pass
        n0 = len(jobs); jobs = [j for j in jobs if (j[9] and (REPOS_NAME.get(j[0], j[0]), j[9], j[10]) not in done_keys)]
        print(f"■ 이어쓰기: 기처리 정리 {len(done_keys)} · 남은 작업 {len(jobs)}/{n0}", flush=True)
    assert jobs, f"정리를 하나도 못 골랐다 — skip={dict(skip)}"
    print(f"■ TRAIN · 정리 {len(jobs)} · 저장소 {len(REPOS)} · 병렬 {JOBS}"
          f" · 건너뜀 {dict(skip)}", flush=True)

    R.OUT = OUT          # run() 은 파일을 안 쓰지만 표시용으로 맞춘다
    S = collections.defaultdict(collections.Counter); nrec = 0
    with open(OUT, "a" if RESUME else "w") as fo, cf.ThreadPoolExecutor(JOBS) as ex:
        for n, recs in enumerate(ex.map(R.run, jobs)):
            for r in recs:
                nrec += 1
                if r["local"]:
                    S[r["proj"]]["지역"] += 1; continue
                S[r["proj"]]["지점"] += 1
                S[r["proj"]]["생존"] += bool(r["ap"] or r["in"] or r["rw"])
                fo.write(json.dumps(r, ensure_ascii=False) + "\n")
            if (n + 1) % 10 == 0:
                print(f"   … {n+1}/{len(jobs)} · 기록 {nrec}", flush=True)
            fo.flush()
    print(f"\n■ TRAIN gold 생존 (지역변수 인자 제외)")
    for p, c in sorted(S.items(), key=lambda x: -x[1]["지점"]):
        n = max(1, c["지점"])
        rate = c["생존"] / n * 100
        print(f"   {p:28s}{c['지점']:6d}{rate:8.1f}%  지역 {c['지역']}")
        # ★ 저장소 건전성 하한 — 지점 50+ 인데 생존 <10% 면 십중팔구
        #   수집 결함이다 (실측 3부류: 사본 오염 5.3% · Type-이론 3.2% ·
        #   경로 매핑 붕괴 22.8%→70%). 조용히 오염 데이터를 쌓지 말고 죽는다.
        assert not (c["지점"] >= 50 and rate < 10.0), \
            f"{p}: 생존 {rate:.1f}% — 수집 결함 의심 (사본/Type-이론/경로매핑 점검)"
    print("TRAIN_POOL_DONE", flush=True)
