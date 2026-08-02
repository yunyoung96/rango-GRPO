# compound 후보(인자) 생성 방법 — `_targeted_cands`

작성 2026-08-01. opener 입력의 "CANDIDATE DECOMPOSITIONS"를 어떻게 조립하나.
코드: `src/tactic_gen/grpo_rollout.py` `_targeted_cands(goals)`.

## 목적
opener/executor가 **compound destruct의 인자**(`destruct (Rle_or_lt 0 x)`)를 스스로 생성하기 어려움(이전 인자 일치 52%). → goal에서 **후보 인자를 결정적으로 조립**해 입력에 넣어줌 → opener가 그중 고르거나 참고. (opener-tac에서 인자 일치 92%로 개선.)

## 입력
goal 문자열을 **첫 빈 줄**로 (가설부 | 결론부) 분리. 가설 `name : type` 파싱.

## ★ 인자를 goal에서 뽑는 실제 알고리즘 (코드 그대로)

"어느 변수를 `{a}`/`{b}`에 넣나, scrutinee E는 어떻게 얻나"의 실제 계산. (`_targeted_cands` 본문)

### (1) 가설 파싱 → (이름들, 타입, head)
`text.split('\n\n',1)[0]`로 가설부만 취한 뒤 각 줄에:
```python
m = re.match(r"^([\w', ]+?)\s*:\s*(.+)$", ln)   # "a b : Z" → 이름부 "a b", 타입 "Z"
typ  = m.group(2).strip()                        # "Z"
head = typ.split()[0]                            # 타입의 첫 토큰 = head ("list nat"→"list")
```
- 한 줄에 여러 변수(`a b c : Z`)면 `re.split(r"[,\s]+", 이름부)`로 각각 분리 → **모두 같은 head 타입**.
- `->`(함수/함의 타입) 포함 줄은 destruct 대상서 제외(단 ④ inversion 후보로는 봄).

### (2) 두 자료구조로 축적
- `dv` = ① 문맥변수 리스트 (head가 `_IND_TYPES`이거나 대문자-inductive, 앞 3개 사용).
- **`byty[head] = [그 타입 변수들]`** ← ③ 결정절차 인자의 핵심. 예: 가설 `a:Z, b:Z, i:positive` → `byty = {'Z':['a','b'], 'positive':['i']}`.

### (3) 인자 대입 = byty에서 순서대로 꺼내 템플릿 format
```python
for head, vs in byty.items():
    if head in _DEC_UN:                              # bool/val/... → 단일
        out.append(f'destruct {vs[0]}.')
    for tmpl in _DEC_CONST.get(head, []):            # Z/R 상수비교 → {a}=vs[0]
        out.append(f'destruct ({tmpl.format(a=vs[0])}).')     # zeq a 0
    if head in _DEC_BIN and len(vs) >= 2:            # 두 동타입 변수 있을 때만
        for tmpl in _DEC_BIN[head]:
            out.append(f'destruct ({tmpl.format(a=vs[0], b=vs[1])}).')  # zeq a b
```
→ **`{a}`=그 타입 첫 변수, `{b}`=둘째 변수.** 그래서 `a:Z,b:Z` → `destruct (zeq a b).` `destruct (zlt a b).` ... 가 나옴. **이변수 템플릿은 같은 타입 변수가 2개 이상일 때만** 생성.

### (4) scrutinee E (② compound 핵심) — 정규식으로 goal에서 추출
```python
for pat in (r'\bmatch\s+(.+?)\s+with\b', r'\bif\s+(.+?)\s+then\b'):
    for m in re.finditer(pat, text):
        e = m.group(1).strip()
        if '\n' not in e and len(e) <= 80 and e.count('(') == e.count(')'):  # balanced
            out.append(f'destruct ({e}).')
```
→ goal에 `match (Rle_or_lt 0 x) with` 있으면 **E=`Rle_or_lt 0 x` 통째**를 인자로 → `destruct (Rle_or_lt 0 x).` (여기선 변수 대입이 아니라 **goal에 이미 쓰인 표현식을 그대로** 인자로 씀.)

### (5) forall 변수 (⑤) — 결론부 정규식
```python
goal_txt = text.split('\n\n',1)[1]
fm = re.search(r'\bforall\s+\(?([\w\s\']+?)\)?\s*[:,]', goal_txt)  # forall x y : ...
→ 앞 2개 nm → induction nm. / destruct nm.
```

### 워크드 예제
가설 `n m : Z`, 결론 `... match (zeq n m) with ...` 라면:
- (1) 파싱: `n,m : Z` → head `Z`, byty `{'Z':['n','m']}`
- (3) ③ _DEC_CONST[Z]: `destruct (zeq n 0).` `destruct (zlt n 0).` `destruct (zle 0 n).` (a=n)
      ③ _DEC_BIN[Z] (len≥2): `destruct (zeq n m).` `destruct (zlt n m).` `destruct (zle n m).` (a=n,b=m)
- (4) ② scrutinee: `destruct (zeq n m).` (goal의 match E 그대로 — ③과 겹치면 dedup)
- ① `destruct n. induction n. destruct m. induction m.`
→ dedup 후 앞 18개가 CANDIDATE 블록.

**요지**: 인자는 두 소스에서 온다 — (a) **문맥 변수를 타입별로 그룹핑해 결정절차 템플릿에 대입**(zeq/zlt/peq...), (b) **goal의 match/if 안 표현식을 통째로**(scrutinee). AST 없이 **문자열 정규식 파싱**이라 한계 있음(중첩·개행·복잡표현 놓침) → 그래서 coq-lsp 유효성 필터로 거름.

## 5단계 후보 조립 (→ dedup → 앞 18개)

### ① 문맥 변수 destruct/induction (앞 3개)
가설 `v : T`에서 head 타입 T가:
- `_IND_TYPES`(nat/positive/Z/N/bool/list/option/comparison/ident/block/val/memval/instruction/sumbool/prod) 이거나
- 대문자로 시작하는 inductive (단 `Type/Set/Prop/R/Q/radix` 제외)
- 단 `->`(함수타입) 아님
→ `destruct v.`, `induction v.`

### ② scrutinee destruct (앞 4개) — **compound의 핵심**
goal 안의 `match E with` / `if E then`에서 **E**(괄호 balanced, ≤80자, 개행 없음) 추출
→ `destruct (E).`
예: `match (Rle_or_lt 0 x) with ...` → `destruct (Rle_or_lt 0 x).`

### ③ 타입-지향 결정절차 템플릿 (CompCert 특화 하드코딩)
가설을 head 타입별로 그룹핑 후:
| 타입 head | 생성 (a=단일변수, b=동타입 2번째) |
|---|---|
| `bool/val/option/comparison/sumbool` (`_DEC_UN`) | `destruct a.` |
| `Z` (`_DEC_CONST`) | `destruct (zeq a 0).` `destruct (zlt a 0).` `destruct (zle 0 a).` |
| `R` (`_DEC_CONST`) | `destruct (Rle_or_lt 0 a).` `destruct (Rlt_le_dec 0 a).` |
| (`_DEC_BIN`: 동타입 변수쌍) | 타입별 이변수 템플릿 |
→ 이게 **compound 인자**(`Rle_or_lt 0 x`, `zeq a 0` 등)를 만드는 핵심. 도메인 결정절차를 goal 변수에 인스턴스화.

### ④ inversion (앞 2개)
가설이 `=`(등식) 포함 또는 이름이 `H*`이고 `->` 아님 → `inversion H.`

### ⑤ forall-bound + induction (일반)
결론 `forall x…`의 x → induction/destruct + generic 첫-premise 귀납 (`induction 1.`)

## 유효성 필터
생성 후보는 **coq-lsp가 검증** — 무효한 후보(그 state에 안 맞음)는 적용 시 INVALID로 버려짐. 즉 후보는 "시도 목록"이고 정답 보장 아님.

## 효과 (측정)
| | 인자 일치(gold) |
|---|---|
| 후보 없이(opener goal만) | 52% |
| **후보+retrieval 입력(opener-tac)** | **92%** |
- gold 열거 포함률: 확장 전 5%(단순 destruct) → 확장 후 **45%**(전체 5단계, **단순+compound 혼합**).

## ★ compound 커버리지 실측 (2026-08-02, 정정판) — "CompCert 모든 compound를 커버하나?" → 약 59%

### ⚠️ 정정: 초기 "~20%"는 측정 버그
초기 측정은 gold `destruct (E) **as [[..]]**`(as절 포함)를 as 없는 후보와 비교해 매칭 실패 → 인위적 저평가. **as절은 destruct 대상과 무관**(이름만 붙임)하니 떼고 비교해야 함. 정정 후:
| 측정 (gold, goldsft_bs2, n=59) | 커버 |
|---|---|
| **전체 방법(`_targeted_cands` ①~⑤)** | **59%** |
- 테이블(③)만의 head 커버는 여전히 낮음(~22%, 455 distinct 미커버 head)이나, **①문맥변수 + ②scrutinee가 나머지를 메워** 전체는 59%.
- 즉 기존 방법이 gold compound의 절반 이상을 이미 후보에 넣음(과거 "20%"는 오류).

**주의**: 이건 **후보생성** 커버리지(gold가 후보 리스트에 드나)지, 모델 선택·coq-lsp 유효성은 별개. n=59 표본 → ±.
- **scrutinee(②)가 커버리지 안 올림**(전체21%≈테이블22%): gold destruct는 대개 **아직 goal에 없는 새 case-split을 생성**하는 것이라 goal의 match/if 스캔으론 못 잡음.
- **미커버 원인 (a)** 결정절차 종류 455 distinct인데 테이블엔 8개(`Int.eq`,`eq_block`,`range_perm_dec`,`valid_access_dec`,`Float.cmp`,`Z.ltb_spec`,`M.elt_eq`,`Genv.find_symbol`...): CompCert 도메인 결정절차가 방대.
- **(b)** 테이블에 있는 head(`zlt/zle/peq/Rle_or_lt`)도 인자 못 맞춤 — "그 타입 첫 두 변수"(vs[0],vs[1]) 휴리스틱인데 gold는 다른 변수/복합표현(`destruct (zlt (f x) (g y))`)을 씀.
- **함의**: `_targeted_cands`는 흔한 Z/positive 패턴을 잡는 **좁은 휴리스틱**이지 CompCert 결정절차 다양성을 포괄 못 함. compound 커버가 벽이면 이 방법으론 부족(스캔은 문자열 정규식이라 근본 한계).

## 코드 참조
- `_targeted_cands()` (5단계 조립), `_scrutinees()` (② match/if 추출), `_DEC_UN/_DEC_CONST/_DEC_BIN` (③ 결정절차 테이블), `_IND_TYPES/_EXCL` (① 타입 필터).
- opener 학습 데이터: `scripts/build_opener_tac_data.py`가 각 state에 `_targeted_cands` 호출해 CANDIDATE 블록 생성.

관련: [[COMPOUND_COMPARISON]] · [[CLOSING_FAILURE_ANALYSIS]] · [[OPENER_TAC]]
