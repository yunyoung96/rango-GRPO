# TRAIN 원본 `.v` 복구 — 외부 조사 (2026-08-18)

> 방법: 5각도 병렬 웹검색 → 18개 1차 출처 fetch → 주장 90개 추출 → 3표 적대적 검증
> (2/3 이상 반증이면 기각) → 확인 13 · 기각 7 · 미검증 5
> 원자료: `/tmp/claude-0/…/tasks/wp16p1n6b.output` (task `wp16p1n6b`, agent 100개)

---

## 0. 질문과 답

**질문** — rango 학습 데이터셋의 원본 `.v` 를 복구할 방법이 있는가?

상황: `/tmp/coq-dataset` 에 `data_points`(파싱된 증명 JSON)와 `sentences.db`(문장 582k행)만
있고 원본 `.v` 가 없다. `sentences.db` 의 `file_path` 가 `/coq-dataset/repos/<owner>-<repo>/…`
를 가리키는데 그 디렉토리가 없다. TRAIN 프로젝트 2,270개(파일 18,911개).

**답 — 있다. 그리고 실제로 복구했다.**

| | |
|---|---|
| 열쇠 | `rkthomps/coq-modeling` 의 **`splits/commits.json`** (214KB) |
| 내용 | `owner/repo` → 40자리 커밋 해시 **2,955쌍** |
| TRAIN 커버리지 | 2,212 / 2,214 저장소 = **99.9%** |
| 실제 복구 결과 | 프로젝트 **2,182/2,270 = 96.1%** · 파일 **17,865/18,911 = 94.5%** · 13GB · `.v` 101,455개 |

**핵심은 "이미 로컬에 있었다"는 것이다.** 7.16GB Zenodo 아티팩트를 다시 받을 필요도,
GitHub 을 다시 긁을 필요도 없었다. 우리 작업트리가 그 저장소의 fork 이므로
`splits/commits.json` 은 처음부터 디스크에 있었다.

---

## 1. 확인된 사실 (13건 중 핵심)

### 1-1. 복구 경로는 존재한다 — `splits/commits.json`

> `{"ytakata69/equivrel": "47cfed8a05ab2d902fbcd3842750681b00f706ac", "mozow01/bizcoq2023": "42884aa4a0a9228bce274e140cee4d799b36efaf", …}`
> — [splits/commits.json](https://github.com/rkthomps/coq-modeling/blob/main/splits/commits.json) · 표결 2-1

값 2,955개가 **전부 정규 40-hex SHA-1** 이라 예외 없이
`git clone https://github.com/<owner>/<repo> && git checkout <hash>` 로 재현된다.

### 1-2. TRAIN split 을 사실상 전량 커버한다 · 표결 3-0

`splits/official-split.json` 의 `train_files` 12,555개가 참조하는 고유 저장소 2,214개 중
**2,212개(99.9%)** 가 `commits.json` 에 해시와 함께 있다. 해시 없는 둘은
`coq-community/corn`(train 294파일) · `coq-community/gaia`(37파일) 뿐이다.

확인된 상위 프로젝트:

```
possientis/Prog                    → bfe2bb4dc5582a9154131b741e0a5615537025e7
HoTT/Coq-HoTT                      → 45af5465b467c0ae9386a2869af73864e8815ea4
LASER-UMASS/TacTok                 → 7d5406147cf329a54a0bb1c38e3af9ee0ff2c84b
uds-psl/coq-library-undecidability → d295433e9f9bf5501e17736c1263b0e4b77007c6
```

### 1-3. 경로 매핑이 결정적이다 · 표결 3-0

`official-split.json` 의 모든 항목이 **로컬 `sentences.db` 의 `file_path` 와 정확히 같은
`repos/<owner>-<repo>/…` 형식**을 쓴다.

```json
{"train_files": [{"dp_name": "0918nobita-Coq-basics.v",
                  "file": "repos/0918nobita-Coq/basics.v",
                  "workspace": "repos/0918nobita-Coq",
                  "repository": "repos/0918nobita-Coq"}, …]}
```

즉 split 파일이 **없어진 `repos/` 트리의 색인** 그 자체다.

### 1-4. 공식 아티팩트는 원본 `.v` 를 배포하지 **않는다**

Zenodo DOI [10.5281/zenodo.14853833](https://doi.org/10.5281/zenodo.14853833)
(concept DOI 10.5281/zenodo.14751621, 3판) — `coq-modeling.tar.gz` 7,159,808,737 바이트,
md5 `29607d3d2513dab2b1c080e5d16bf5ef`, MIT, 인증 없이 다운로드 가능(HTTP 200 확인).

그런데 아티팩트가 담은 것은 **우리가 이미 가진 형태 그대로**다:

> "This artifact contains the entire corpus of data used to train and evaluate Rango.
> The data resides in the raw-data folder … coq-dataset / coqstoq-test / coqstoq-val / coqstoq-cutoff"
> — 아카이브 안의 `README.md`

그리고 `Dockerfile` 은 **평가 split 세 개에만** 실제 `.v` 를 만든다:

```dockerfile
RUN python3 coqstoq/build_projects.py
COPY ./raw-data /app/coq-modeling/raw-data
RUN ln -s /app/coq-modeling/CoqStoq/test-repos raw-data/coqstoq-test/repos
RUN ln -s /app/coq-modeling/CoqStoq/val-repos  raw-data/coqstoq-val/repos
```

`raw-data/coq-dataset` 에는 `repos` 를 **아예 안 만든다.** `.dockerignore` 의 마지막 항목이
train repos 경로다. **TRAIN 경로가 dangling 인 것은 설계다.**

→ **7.16GB 를 다시 받아도 원본 `.v` 는 안 나온다.** (이 결론이 "받아보면 되지 않나" 를 잘라 준다.)

### 1-5. 다른 배포 경로는 없다 · 표결 3-0

`rkthomps/CoqStoq` 는 **GitHub 릴리스가 0개**다 ("There aren't any releases here").
릴리스 에셋으로 받는 길은 없다.

---

## 2. 기각된 주장 (7건)

적대적 검증에서 **죽은** 주장들이다. 같은 생각이 다시 떠오를 때 되풀이하지 않으려고 남긴다.

| 기각된 주장 | 표결 | 왜 틀렸나 |
|---|---|---|
| "CoqStoq 에는 TRAIN split 이 없으니 복구 불가" | 0-3 | CoqStoq 에는 없지만 **coq-modeling 의 `splits/`** 에 있다. 저장소를 잘못 봤다 |
| "`.gitmodules` 의 20개 프로젝트가 전부 — TRAIN 커버리지 0" | 0-3 | 같은 오류. 평가 split 만 보고 결론냈다 |
| "TRAIN 은 2023-11-05 GitHub 스냅샷의 잔여집합이라 재도출해야 한다" | 0-3 | 해시가 **박혀 있으므로** 재스크레이핑 불필요 |
| "아티팩트에 아무것도 안 빠졌다" | 0-3 | 원본 `.v` 가 빠졌다 |
| "TRAIN `.v` 는 공개된 적이 없다" | 0-3 | `.v` 자체는 아니지만 **재현 키**가 공개돼 있다 |
| "하이픈 평탄화 `<owner>-<repo>` → `owner/repo` 는 기계적으로 역산된다" | 1-2 | **owner 이름 자체에 하이픈이 있으면 모호**하다(`uds-psl/…`, `coq-community/…`). `commits.json` 키와 대조해야 한다 |
| "Zenodo 가 유일 채널" | 1-2 | GitHub 저장소도 채널이다 |

**하이픈 모호성**은 실제 함정이었다 — `repos/uds-psl-coq-library-undecidability` 를
`uds/psl-coq-library-undecidability` 로 자르면 안 된다. `commits.json` 키 집합과
맞춰 보는 것이 유일하게 안전한 방법이다.

---

## 3. 실제 복구 결과 (2026-08-18 실행)

스크립트: `scripts/recover_train_repos.py` · 커밋 `98ab921` → `04af006`

```
프로젝트 2,182 / 2,270 = 96.1%
파일     17,865 / 18,911 = 94.5%
용량     13GB · .v 101,455개
```

**실패 88개(파일 1,046개)는 전부 GitHub 404** — 수집 이후 삭제되거나 비공개로 바뀐
저장소다(`yj-han/software-foundations`, `addap/autosubst-ocaml` 등 확인).
`coq-community/corn`·`gaia` 는 `commits.json` 에 해시가 없어 제외했다.

> **함정 하나** — VS Code 원격 컨테이너의 git askpass 가 깨져 있어
> (`Cannot find module /tmp/vscode-remote-containers-*.js`) 없는 저장소에서 나는 오류가
> 가려졌다. `GIT_TERMINAL_PROMPT=0` + askpass 환경변수 제거로 진짜 원인(404)이 드러났다.

현재 상태: `/tmp/coq-dataset/repos` — 2,182 디렉토리 · `.v` 101,460개 · 13GB.

---

## 4. 왜 이게 중요했나

원본 `.v` 가 있어야 하는 이유는 **`sentences.db` 가 문장 단위로만 저장돼 있어서**다.
`Require Import` · `Section` · `Variable` 선언이 통째로 빠져 있어 파일을 재구성하면
**1/8 만 컴파일된다.** 원본이 없으면:

- `scripts/build_cuts.py` 가 `Check (L a b).` 로 cut 명제를 못 얻는다
- 펑터 인스턴스 인덱스(`build_functor_*.py`)를 못 만든다
- 학습 예제의 "gold lemma 가 실제로 무엇인가" 를 확인할 수 없다

복구 이후 이것들이 전부 가능해졌다.

---

## 5. 출처 (1차 18건)

| URL | 성격 |
|---|---|
| [splits/commits.json](https://github.com/rkthomps/coq-modeling/blob/main/splits/commits.json) | ★ 복구 열쇠 |
| [splits/official-split.json](https://github.com/rkthomps/coq-modeling/blob/main/splits/official-split.json) | ★ 파일 색인 |
| [zenodo.org/records/14853833](https://zenodo.org/records/14853833) · [DOI](https://doi.org/10.5281/zenodo.14853833) | 공식 아티팩트 7.16GB |
| [zenodo API versions](https://zenodo.org/api/records/14853833/versions?size=20) | 판본 3개 |
| [arxiv 2412.14063](https://arxiv.org/abs/2412.14063) · [v1](https://arxiv.org/html/2412.14063v1) · [v2](https://arxiv.org/html/2412.14063v2) | Rango 논문 (ICSE 2025) |
| [rkthomps/CoqStoq](https://github.com/rkthomps/CoqStoq) | 벤치마크 (릴리스 0) |
| [ARTIFACT.md](https://github.com/rkthomps/coq-modeling/blob/main/ARTIFACT.md) | 아티팩트 설명 |
| [rkthomps/coq-modeling](https://github.com/rkthomps/coq-modeling) | 상류 저장소 |
| [zenodo 10028721](https://zenodo.org/records/10028721) | 선행 코퍼스 |
| [CoqGym coq_projects](https://github.com/princeton-vl/CoqGym/tree/master/coq_projects) | 대체 출처 후보 |
| [Radiance-Technologies/prism](https://github.com/Radiance-Technologies/prism) · [arxiv 2405.04282](https://arxiv.org/html/2405.04282v1) | Coq 코퍼스 도구 |
| [sr-lab/coqpyt](https://github.com/sr-lab/coqpyt) | Coq 파싱 |
| [possientis/Prog](https://github.com/possientis/Prog) | TRAIN 최대 프로젝트 |

---

## 6. 재현

```bash
python3 - <<'PY'
import json, collections
cm = json.load(open("splits/commits.json"))
sp = json.load(open("splits/official-split.json"))
repos = {f["repository"].removeprefix("repos/") for f in sp["train_files"]}
keys  = {k.replace("/", "-"): k for k in cm}          # 하이픈 평탄화 역매핑
hit   = {r for r in repos if r in keys}
print(f"TRAIN 저장소 {len(repos)} · 해시 있음 {len(hit)} = {len(hit)/len(repos)*100:.1f}%")
print("없는 것:", sorted(repos - hit))
PY

# 실제 복구
GIT_TERMINAL_PROMPT=0 python3 scripts/recover_train_repos.py 400
```
