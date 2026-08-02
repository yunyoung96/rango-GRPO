"""rango-augmented 구조컨텍스트 생성 — 학습·추론·스크립트가 공유하는 canonical 로직.
train/infer 동일 규칙 보장(REVIEW.md R1). CPU only.

selective_types(goal): goal의 **가설 + 결론** 양쪽에서 inductive 타입을 뽑아 생성자 주입.
  - 가설 `x : T`의 T (destruct 대상)
  - 결론에 literal로 등장하는 inductive 타입명 (43% goal이 결론에만 있는 타입 보유 — 가설만 보면 놓침)
  - 소수생성자(≤8) 필터, 결론관련 우선, top-K + 토큰예산 캡.
"""
import re

_KW = {'forall', 'exists', 'fun', 'match', 'if', 'then', 'else', 'let', 'in', 'with', 'end',
       'Type', 'Prop', 'Set', 'return', 'as', 'is', 'and', 'or', 'of', 'at', 'struct', 'fix', 'cofix'}

def _bad_head(h):
    s = (h or '').split('.')[-1]
    return (s in _KW) or len(s) < 2

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
