import os
"""rango-augmented 구조컨텍스트 생성 — 학습·추론·스크립트가 공유하는 canonical 로직.
train/infer 동일 규칙 보장(REVIEW.md R1). CPU only.

selective_types(goal): goal의 **가설 + 결론** 양쪽에서 inductive 타입을 뽑아 생성자 주입.
  - 가설 `x : T`의 T (destruct 대상)
  - 결론에 literal로 등장하는 inductive 타입명 (43% goal이 결론에만 있는 타입 보유 — 가설만 보면 놓침)
  - 소수생성자(≤8) 필터, 결론관련 우선, top-K + 토큰예산 캡.

definitions(goal): goal 결론의 **정의된 함수**의 정의문을 주입(PHASE2_DECIDER_GUIDE §D3).
  - 현재 프롬프트는 함수 이름만 주고 정의는 0% → "완전한 상태" 복원이 목적.
  - proof-독립(goal만 봄). unfold 빈도 같은 proof 유래 신호 금지(=누수).
  - ★ 길이 규칙: 정의가 길면 시그니처만, 시그니처도 길면 **아예 안 넣음**.
"""
import re

_KW = {'forall', 'exists', 'fun', 'match', 'if', 'then', 'else', 'let', 'in', 'with', 'end',
       'Type', 'Prop', 'Set', 'return', 'as', 'is', 'and', 'or', 'of', 'at', 'struct', 'fix', 'cofix'}

def _bad_head(h):
    s = (h or '').split('.')[-1]
    if (s in _KW) or len(s) < 2:
        return True
    # ★ 표준 라이브러리 타입은 [TYPES]/[DEFINITIONS] 에 넣지 않는다.
    #   `Inductive list A := nil | cons` 를 프롬프트에 넣는 것은 토큰 낭비다 —
    #   그 토큰으로 premise 를 더 넣는 편이 낫다.
    #   실측: 후보 풀의 92.7% 가 stdlib. [PREMISES] 예산이 빡빡해
    #   프롬프트에 10~22개만 들어가는 상황이라 이 절약이 직접적으로 도움이 된다.
    #   끄려면 INJECT_SKIP_STDLIB=0.
    if os.environ.get("INJECT_SKIP_STDLIB", "1") == "1":
        try:
            from tactic_gen.normalize_names import is_stdlib_name
            import os as _os
            _prev = _os.environ.get("NORMALIZE_SKIP_STDLIB")
            _os.environ["NORMALIZE_SKIP_STDLIB"] = "1"   # 이 판정은 정규화 설정과 독립
            r = is_stdlib_name(s)
            if _prev is None:
                _os.environ.pop("NORMALIZE_SKIP_STDLIB", None)
            else:
                _os.environ["NORMALIZE_SKIP_STDLIB"] = _prev
            if r:
                return True
        except Exception:
            pass
    return False

def _split_goal(goal):
    parts = (goal or '').split('\n\n', 1)
    hyp = parts[0]
    concl = parts[1] if len(parts) > 1 else (goal or '')
    return hyp, concl

def hyp_types(goal):
    """가설 블록의 (변수명, 타입head) 목록."""
    hyp, _ = _split_goal(goal)
    out = []
    for ln in hyp.split('\n'):
        m = re.match(r"^\s*([\w', ]+?)\s*:\s*(.+)$", ln)
        if not m:
            continue
        typ = m.group(2).strip()
        head = typ.split()[0].split('.')[-1] if typ.split() else typ
        for nm in re.split(r"[,\s]+", m.group(1).strip()):
            if nm:
                out.append((nm, head))
    return out

def selective_types(goal, ind_index, max_types=6, max_ctors=8, budget_tok=200, ntok=None):
    """가설+결론에서 inductive 타입 뽑아 '[T := c1 | c2 ...]' 라인 리스트 반환.
    ind_index: {타입명: [생성자...]}. ntok(s)->int 토큰카운터(없으면 단어수 근사).
    반환: [(head, line), ...] (예산·개수 캡 적용)."""
    if ntok is None:
        ntok = lambda s: max(1, len(re.findall(r'\S+', s or '')))
    hyp, concl = _split_goal(goal)
    concl_ids = set(re.findall(r"[A-Za-z_][\w']*", concl))
    cands, seen = [], set()
    # ① 가설 변수의 타입 (destruct 대상)
    for nm, head in hyp_types(goal):
        if head in seen or _bad_head(head):
            continue
        if head in ind_index and len(ind_index[head]) <= max_ctors:
            seen.add(head)
            score = (2 if nm in concl_ids else 1) - 0.05 * len(ind_index[head])
            cands.append((score, head))
    # ② 결론에 literal 등장하는 inductive 타입명 (가설에 없어도 — 43% goal이 여기 해당)
    for name in concl_ids:
        if name in seen or _bad_head(name):
            continue
        if name in ind_index and len(ind_index[name]) <= max_ctors:
            seen.add(name)
            cands.append((1.5 - 0.05 * len(ind_index[name]), name))   # 결론 등장 타입도 포함
    cands.sort(key=lambda x: (-x[0], x[1]))   # 점수순, 동점은 이름순(결정적)
    lines, tot = [], 0
    for _, head in cands[:max_types]:
        line = f"{head} := {' | '.join(ind_index[head])}"
        t = ntok(line)
        if tot + t > budget_tok:
            break
        lines.append((head, line))
        tot += t
    return lines


# ── [DEFINITIONS]: goal 결론에 등장하는 함수의 정의 (PHASE2_DECIDER_GUIDE §D3) ──
#   로컬변수(H, IH, x, n 같은 1~2글자)·키워드는 제외. 인덱스에 있는 이름만 통과하므로
#   인덱스 자체가 1차 필터 역할을 한다.
_LOCAL = re.compile(r"^(H\w*|IH\w*|[a-z]\d?|in|at|of|as|to|by|is)$")


def _norm_proj(p):
    return re.sub(r'[^a-z0-9]', '', (p or '').lower())


def project_of(file_name):
    """LmExample.file_name('repos/compcert/flocq/IEEE754/Binary.v') → 'compcert'.
    ※ pick_def 에는 **file_name 전체**를 넘기는 게 정확하다(같은 저장소 안 충돌 때문)."""
    p = (file_name or '').replace('\\', '/')
    m = re.search(r'(?:^|/)repos/([^/]+)/', p)
    return m.group(1) if m else None


def _rel_path(file_name):
    """'repos/<proj>/a/b/c.v' → '<proj>/a/b/c.v' (인덱스 키와 같은 형식)."""
    p = (file_name or '').replace('\\', '/')
    m = re.search(r'(?:^|/)repos/(.+)$', p)
    return m.group(1) if m else p.lstrip('/')


def pick_def(cands, where=None):
    """이름 하나의 후보들({파일경로: 정의}) 중 **맞는 것**을 고른다. 못 고르면 None(=주입 안 함).

    where 는 goal 이 나온 파일(LmExample.file_name). 우선순위:
      ① 같은 파일  ② 같은 디렉토리  ③ 같은 프로젝트  ④ stdlib  ⑤ 후보 1개  ⑥ 그 외 스킵

    ★ 왜 파일까지 보나 (실패에서 배움): 프로젝트 단위로만 고르면, 한 저장소가 독립 벤치마크를
      여럿 담은 경우 **다른 벤치마크의 동명 정의**가 들어간다. 실제로 goal 이
      `forall x : Lst, append x nil = x` 인데 `append (l1 : lst) ... | Nil | Cons` 를 주입했고
      (대소문자·생성자 전부 불일치), 정작 같은 파일에 `append (… : Lst) : Lst` 정답이 있었다.
    """
    if not cands:
        return None
    if isinstance(cands, str):            # 구버전 인덱스({이름: 정의문}) 호환
        return cands
    if where:
        rel = _rel_path(where)
        # ★ 예제 경로와 인덱스 키는 **프로젝트 표기가 다르다**:
        #     예제  repos/compcert/flocq/IEEE754/Binary.v → compcert/flocq/IEEE754/Binary.v
        #     인덱스 AbsInt-CompCert/flocq/IEEE754/Binary.v
        #   예전엔 ①·②를 문자열 그대로 비교해서 **CompCert 에서 항상 실패**했고,
        #   결국 ③(프로젝트 단위)로 떨어져 같은 프로젝트 내 아무 정의나 골랐다.
        #   실측: 같은 파일/디렉토리에 정답이 있는 1349건 중 **654건(48.5%)에 다른 정의**를 주입.
        #   → 첫 경로 요소만 ③과 같은 규칙(정규화 후 부분일치)으로 비교한다.
        def _split1(p):
            a = p.split('/', 1)
            return a[0], (a[1] if len(a) > 1 else '')

        def _proj_eq(a, b):
            x, y = _norm_proj(a), _norm_proj(b)
            return x == y or bool(x) and (x in y or y in x)

        rp, rrest = _split1(rel)
        for k, v in cands.items():                         # ① 같은 파일
            kp, krest = _split1(k)
            if krest == rrest and _proj_eq(kp, rp):
                return v
        d_of = lambda x: x.rsplit('/', 1)[0] if '/' in x else ''
        for k, v in cands.items():                         # ② 같은 디렉토리
            kp, krest = _split1(k)
            if d_of(krest) == d_of(rrest) and _proj_eq(kp, rp):
                return v
        for k, v in cands.items():                         # ③ 같은 프로젝트
            kp, _ = _split1(k)
            if _proj_eq(kp, rp):
                return v
    if 'stdlib' in cands:                                  # ④ stdlib
        return cands['stdlib']
    if len(cands) == 1:                                    # ⑤ 유일
        return next(iter(cands.values()))
    return None                                            # ⑥ 애매 → 안 넣음


def definitions(goal, func_index, project=None, max_defs=5, budget_tok=200,   # project = file_name(경로 전체)
                max_body=80, max_sig=40, ntok=None, exclude=None):
    """goal 결론의 정의된 함수 → [(함수명, 정의문), ...]. proof-독립(goal 만 봄).

    길이 규칙(★ 너무 긴 정의는 넣지 않는다):
      · 정의문 ≤ max_body 토큰      → 정의문 그대로
      · max_body 초과               → ':=' 앞 **시그니처만** (큰 재귀함수 대응)
      · 시그니처도 max_sig 초과     → **스킵**(아예 안 넣음). 프롬프트를 잡아먹느니 빼는 게 낫다.
      · 누적 budget_tok 초과분       → 스킵(다음 후보 계속 시도 — 짧은 정의는 들어갈 수 있게)
    개수가 작아 랭킹은 불필요(가이드 D1) — 이름순 정렬로 결정성만 보장한다.
    """
    if ntok is None:
        ntok = lambda s: max(1, len(re.findall(r'\S+', s or '')))
    hyp, concl = _split_goal(goal)
    local_names = {nm for nm, _ in hyp_types(goal)}          # 가설 변수명 = 로컬(전역함수 아님)
    heads = set()
    for t in re.findall(r"[A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*", concl or ""):
        s = t.split('.')[-1]
        if _bad_head(s) or _LOCAL.match(s) or s in local_names:
            continue
        heads.add(s)
    skip = {s for s in (exclude or ())}                       # [TYPES] 가 이미 보여준 이름은 중복
    lines, tot = [], 0
    for h in sorted(heads):                                   # 결정적(이름순)
        if h in skip:
            continue
        d = pick_def(func_index.get(h), project)              # 프로젝트 우선, 애매하면 None
        if not d:
            continue
        if ntok(d) > max_body:
            d = d.split(':=')[0].strip()                      # 시그니처만
            if ntok(d) > max_sig:
                continue                                      # ★ 그래도 길면 스킵
            if ':' not in d:
                continue                                      # 타입 없는 껍데기(`Definition f x`) = 무정보 → 스킵
        t = ntok(d)
        if tot + t > budget_tok:
            continue                                          # 예산 초과분만 건너뜀
        lines.append((h, d))
        tot += t
        if len(lines) >= max_defs:
            break
    return lines


# ══════════════════════════════════════════════════════════════════════════════
# v2 — main(b1dd53a) 설계와 현재 구현의 장점을 합친 버전 (AUGMENT_V2=1)
#   · [TYPES]      : 생성자 **이름만** → **정의문 전체**(생성자 인자 타입 포함) + **재귀**(depth1)
#                    실패로그 근거: "Expects a disjunctive pattern with 2/3 branches" 287건 —
#                    생성자 인자 개수를 알아야 destruct 패턴을 맞춘다. 이름만으론 알 수 없다.
#   · [DEFINITIONS]: 시드는 **우리 방식 유지**(결론의 모든 식별자). main 의 'f(' 시드는 Coq 관용구
#                    (`f x`)와 안 맞아 gold unfold 적중률 21.6% vs 우리 70.7%(실측). 여기에 main 의
#                    **재귀(depth1)** 만 도입 — `pred := -succ(-x)` 처럼 정의가 다른 정의를 부를 때 유용.
#   · 공통          : 프로젝트별 정의 선택(이름 충돌 방지) 유지, stdlib 는 leaf(재귀 중단·주입 생략).
# ══════════════════════════════════════════════════════════════════════════════

# 모델이 이미 아는 stdlib 타입/함수 — 주입하지 않고 재귀도 여기서 멈춘다(폭발 방지).
_STDLIB = {'nat', 'Z', 'positive', 'N', 'bool', 'list', 'option', 'prod', 'sum', 'unit',
           'comparison', 'sumbool', 'sumor', 'sig', 'ex', 'and', 'or', 'eq', 'byte',
           'int', 'int64', 'float', 'float32', 'Q', 'R', 'True', 'False', 'ascii',
           'string', 'le', 'lt', 'nil', 'cons', 'None', 'Some', 'pair', 'S', 'O'}

_TYPE_KINDS = ('Inductive', 'CoInductive', 'Variant', 'Record', 'Structure', 'Class')


def _is_type_def(defn):
    """정의문이 타입 선언인가(Inductive/Record/...) 아니면 함수(Definition/Fixpoint)인가."""
    head = (defn or '').split()
    i = 0
    while i < len(head) and (head[i].startswith('#[') or head[i] in ('Local', 'Global', 'Polymorphic', 'Monomorphic')):
        i += 1
    return i < len(head) and head[i] in _TYPE_KINDS


def _shorten(defn, ntok, cap, want_type=False):
    """긴 정의 축약: ':=' 앞 시그니처 → 그래도 길면 앞부분만 남기고 '...'.

    ★ `want_type=True`(Inductive/Record)면 **시그니처만 남기지 않는다.**
      타입은 **생성자 목록이 핵심**인데 시그니처만 주면 아무 정보가 없다:

          Inductive f1 (clo: rel->rel) (r: rel): rel        ← 생성자 0개. 쓸모없다

      실측 300 예제 중 21건(7%)이 이 형태였다. 프롬프트 자리만 먹고 모델은
      "T0 의 생성자가 뭔가"를 여전히 못 읽는다. 넣지 않고 **자리를 다른 타입에 넘긴다.**
      (함수는 반대다 — `Definition f : A -> B` 시그니처만으로도 타입 정보가 된다.)
    """
    if ntok(defn) <= cap:
        return defn
    sig = defn.split(':=')[0].strip()
    if ':' in sig and ntok(sig) <= cap:
        return None if want_type else sig
    if want_type:
        return None                      # 잘라서 넣느니 안 넣는다
    w = defn.split()
    while w and ntok(' '.join(w) + ' ...') > cap:
        w = w[:-1]
    return (' '.join(w) + ' ...') if w else None


def _expand(seeds, index, project, want_type, ntok, budget, max_items, cap, depth=1):
    """시드에서 시작해 정의를 모으고(재귀 depth), 예산/개수 캡을 적용. [(name, line), ...] 반환."""
    seen, order, frontier, d = set(), [], list(seeds), 0
    while frontier and d <= depth:
        nxt = []
        for name in frontier:
            if name in seen or name in _STDLIB:
                continue
            seen.add(name)
            defn = pick_def(index.get(name), project)
            if not defn or _is_type_def(defn) != want_type:
                continue
            order.append((name, defn))
            body = defn.split(':=', 1)[-1]
            for r in re.findall(r"[A-Za-z_][\w']*", body):        # 재귀: 정의가 참조하는 이름
                if r not in seen and r not in nxt and r not in _STDLIB \
                        and not _bad_head(r) and r in index:
                    nxt.append(r)
        frontier = nxt
        d += 1
    lines, tot = [], 0
    for name, defn in order:
        s = _shorten(defn, ntok, cap, want_type=want_type)
        if not s:
            continue
        t = ntok(s)
        if tot + t > budget:
            continue                      # 예산 초과분은 건너뛰고 짧은 뒤 후보를 계속 시도
        lines.append((name, s))
        tot += t
        if len(lines) >= max_items:
            break
    return lines


def types_v2(goal, index, project=None, budget_tok=300, max_types=8, cap=60, ntok=None, depth=1):
    # project = LmExample.file_name(경로 전체). pick_def 가 파일→디렉토리→프로젝트 순으로 좁힌다.
    """[TYPES] v2: goal(가설+결론)의 타입 → **정의문**(생성자 인자 포함) + 재귀. 가설 타입 우선."""
    if ntok is None:
        ntok = lambda s: max(1, len(re.findall(r'\S+', s or '')))
    hyp, concl = _split_goal(goal)
    concl_ids = set(re.findall(r"[A-Za-z_][\w']*", concl))
    seeds, seen = [], set()
    for _, head in hyp_types(goal):                    # ① 가설 변수의 타입(destruct 대상) 최우선
        if head not in seen and not _bad_head(head):
            seen.add(head); seeds.append(head)
    for name in sorted(concl_ids):                     # ② 결론 등장 타입
        if name not in seen and not _bad_head(name):
            seen.add(name); seeds.append(name)
    return _expand(seeds, index, project, True, ntok, budget_tok, max_types, cap, depth)


def definitions_v2(goal, index, project=None, budget_tok=300, max_defs=8, cap=60, ntok=None, depth=1):
    # project = LmExample.file_name(경로 전체).
    """[DEFINITIONS] v2: 시드는 결론의 모든 식별자(현행 유지 — gold unfold 적중 70.7%) + 재귀 depth1."""
    if ntok is None:
        ntok = lambda s: max(1, len(re.findall(r'\S+', s or '')))
    hyp, concl = _split_goal(goal)
    local = {nm for nm, _ in hyp_types(goal)}
    seeds = []
    for t in re.findall(r"[A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*", concl or ''):
        s = t.split('.')[-1]
        if _bad_head(s) or _LOCAL.match(s) or s in local or s in seeds:
            continue
        seeds.append(s)
    return _expand(seeds, index, project, False, ntok, budget_tok, max_defs, cap, depth)
