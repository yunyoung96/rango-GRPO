"""rango-augmented 구조컨텍스트 — 학습·추론·스크립트 공유 canonical 로직. CPU only.
[TYPES]: goal(가설+결론) 타입 → **재귀**(stdlib leaf) → 랭킹(가설변수 우선) → 예산캡.
[DEFINITIONS]: goal 결론 함수 → **재귀**(stdlib leaf) → 예산캡. (전이: 인덱스는 전체 코퍼스)
근거: docs/grpo/rango_augmented/AUGMENTED_FINAL.md (실측 커버100%·안터짐).
"""
import re, json, os

_KW = {'Type', 'Set', 'Prop', 'Inductive', 'Definition', 'Record', 'Variant', 'Fixpoint',
       'forall', 'exists', 'fun', 'match', 'with', 'end', 'let', 'in', 'if', 'then', 'else',
       'return', 'as', 'struct', 'fix', 'cofix', 'is', 'of', 'at'}

# 인덱스 lazy-load (env로 경로 override 가능)
_TYPE_IDX = None   # {name: [def, is_stdlib]}
_FUNC_IDX = None
def _load():
    global _TYPE_IDX, _FUNC_IDX
    if _TYPE_IDX is None:
        try:
            _TYPE_IDX = json.load(open(os.environ.get("TYPE_INDEX", "data/type_defs.json")))
        except Exception:
            _TYPE_IDX = {}
    if _FUNC_IDX is None:
        try:
            _FUNC_IDX = json.load(open(os.environ.get("FUNC_INDEX", "data/func_defs.json")))
        except Exception:
            _FUNC_IDX = {}
    return _TYPE_IDX, _FUNC_IDX

def _split(goal):
    parts = (goal or '').split('\n\n', 1)
    return parts[0], (parts[1] if len(parts) > 1 else (goal or ''))

def _ids(txt):
    return set(x.split('.')[-1] for x in re.findall(r"[A-Za-z_][\w'\.]*", txt or ''))

def _short(defn, ntok, cap):
    return defn if ntok(defn) <= cap else ' '.join(defn.split()[:cap-10]) + ' ...'

def _refs(defn, index):
    """정의 안에서 참조하는 (index에 있는) 이름들 — 재귀 대상."""
    return {x for x in _ids(defn) if x in index and x not in _KW}


def selective_types(goal, ind_index=None, max_types=8, max_ctors=8,
                    budget_tok=300, ntok=None, max_depth=1):
    """[TYPES]: 가설+결론 타입 → 재귀(stdlib leaf) → 랭킹 → 캡. 반환 [(name, line), ...].
    ind_index 인자는 하위호환용(무시하고 _TYPE_IDX 사용). max_depth=1 권장(실측)."""
    if ntok is None:
        ntok = lambda s: max(1, len(re.findall(r'\S+', s or '')))
    tidx, _ = _load()
    if not tidx:
        return []
    hyp, concl = _split(goal)
    hyp_types = set()
    for m in re.finditer(r':\s*([A-Za-z_][\w\'\.]*)', hyp):
        hyp_types.add(m.group(1).split('.')[-1])
    concl_ids = _ids(concl)
    # 시드 = 가설 + 결론 타입
    seed = [t for t in (hyp_types | concl_ids) if t in tidx]
    # 재귀 수집 (stdlib은 정의 넣되 재귀 안 함 = leaf; 여기선 stdlib는 주입도 제외)
    seen, order, frontier, depth = set(), [], list(seed), 0
    while frontier and depth <= max_depth:
        nxt = []
        for t in frontier:
            if t in seen:
                continue
            seen.add(t)
            defn, is_std = tidx[t]
            if is_std:
                continue                      # stdlib = leaf + 주입 제외 (모델이 앎)
            order.append((t, depth))
            for r in _refs(defn, tidx):
                if r not in seen and r not in nxt:
                    nxt.append(r)
        frontier = nxt
        depth += 1
    # 랭킹: 가설변수 타입(+10) > 결론등장(+5) > depth 낮음 > 생성자 적음
    def score(t, d):
        defn = tidx[t][0]
        ctors = defn.count('|') + 1
        return (10 if t in hyp_types else 0) + (5 if t in concl_ids else 0) \
               + (max_depth - d) * 2 + max(0, 3 - ctors * 0.2)
    order.sort(key=lambda x: -score(x[0], x[1]))
    lines, tot = [], 0
    for t, _ in order[:max_types * 3]:
        defn = tidx[t][0]
        if defn.count('|') + 1 > max_ctors and t not in hyp_types:
            pass  # 큰 타입도 가설변수면 넣음
        line = _short(defn, ntok, 50)
        tk = ntok(line)
        if tot + tk > budget_tok:
            break
        lines.append((t, line))
        tot += tk
        if len(lines) >= max_types:
            break
    return lines


def definitions(goal, budget_tok=300, ntok=None, max_depth=1, max_defs=6):
    """[DEFINITIONS]: goal 결론의 정의된 함수 → 재귀(stdlib leaf) → 캡. 반환 [(name, line), ...]."""
    if ntok is None:
        ntok = lambda s: max(1, len(re.findall(r'\S+', s or '')))
    _, fidx = _load()
    if not fidx:
        return []
    _, concl = _split(goal)
    # 시드 = 결론의 함수적용/대문자 (도메인 함수만)
    seed = set()
    for m in re.finditer(r"([A-Za-z_][\w'\.]*)\s*\(", concl):
        seed.add(m.group(1).split('.')[-1])
    for m in re.finditer(r"\b([A-Z][\w'\.]*)", concl):
        seed.add(m.group(1).split('.')[-1])
    seed = [f for f in seed if f in fidx and not fidx[f][1] and len(f) > 1 and f not in _KW]
    seen, order, frontier, depth = set(), [], list(seed), 0
    while frontier and depth <= max_depth:
        nxt = []
        for f in frontier:
            if f in seen:
                continue
            seen.add(f)
            defn, is_std = fidx[f]
            if is_std:
                continue
            order.append(f)
            for r in _refs(defn, fidx):
                if not fidx.get(r, ['', True])[1] and r not in seen and r not in nxt:
                    nxt.append(r)
        frontier = nxt
        depth += 1
    lines, tot = [], 0
    for f in order:
        line = _short(fidx[f][0], ntok, 60)
        tk = ntok(line)
        if tot + tk > budget_tok:
            break
        lines.append((f, line))
        tot += tk
        if len(lines) >= max_defs:
            break
    return lines
