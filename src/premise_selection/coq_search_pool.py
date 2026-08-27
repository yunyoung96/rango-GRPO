"""★ **Coq 내장 색인(`SearchPattern`/`SearchRewrite`)이 찾은 lemma 를 검색 풀에 합친다.**

## 왜 합집합인가 (필터가 아니라)

실측(CompCert 120 지점 · 선언 이름 기준):

    ① 현행 rango 풀        후보 1,333   gold 포함 51.7%
    ② Coq Search 결과      후보 3,077   gold 포함 **69.2%**
    ③ ①∩② (필터로 쓸 때)    후보   321   gold 포함  35.8%   ← gold 를 31% 잃는다
    ④ **①∪②**             후보 4,090   gold 포함 **85.0%**

② 는 **전역 환경 전체**에서 뽑으므로 ①(프로젝트 한정)보다 넓고, 그런데도 gold 포함이
더 높다. 즉 이것은 **축소 도구가 아니라 도달성 도구**다. 교집합으로 좁히면 ① 밖에
있던 gold 를 통째로 버린다.

랭커가 뒤에서 순위를 매기므로 **후보가 느는 비용보다 gold 가 아예 없는 것이 훨씬 비싸다**
(현행 48.3% 가 그렇다). checkpoint47000 §4 의 "커버리지 개선만 값을 낸다(+6.2pp)" 와
같은 방향이다.

## 어떻게 붙나

검색(`example_from_step`)은 Coq 세션이 없다. 그래서 **주입식**으로 만든다 —
탐색기(`ProofManager` 를 들고 있는 쪽)가 goal 마다 질의를 돌려 결과를 여기에 넣어 두면,
`lm_example` 이 풀을 만들 때 꺼내 **랭킹 전에** 합친다(공정 경쟁).

    coq_search_pool.put(key, names)      ← 탐색기가 채운다
    coq_search_pool.extra(key, …)        ← lm_example 이 꺼낸다

세션이 없으면(학습·오프라인) 조용히 빈 목록이라 **동작이 안 바뀐다**.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
from typing import Optional

# ── 설정 (파이썬 변수 — 환경변수 아님) ────────────────────────────────────────
ENABLED = True          # 풀 합치기를 켠다
MAX_ADD = 400           # 한 스텝에 합칠 최대 개수 (랭커가 감당할 규모로)
PRIORITIZE = False      # ★ 끈다 — 실측으로 손해 (아래 prioritize 설명)
PRIORITY_TOP = 8        # 켤 때 앞에 둘 개수 (참고용)
ELAB_INDEX = "data/elab_compcert.jsonl"   # 이름 → elaborate 타입 (선언문 생성용)

_lock = threading.Lock()
_found: dict = {}
_stmt: Optional[dict] = None
_con = None


def put(key, names) -> None:
    """탐색기가 goal 마다 질의 결과를 넣는다. `key` 는 (파일, 증명, 스텝) 같은 무엇이든."""
    with _lock:
        _found[key] = list(dict.fromkeys(names))[:MAX_ADD * 2]


def clear() -> None:
    with _lock:
        _found.clear()


def _index() -> dict:
    """이름 → 선언문. elaborate 색인을 먼저, 없으면 sentence DB 를 본다."""
    global _stmt
    if _stmt is not None:
        return _stmt
    _stmt = {}
    if os.path.exists(ELAB_INDEX):
        for ln in open(ELAB_INDEX):
            ln = ln.strip()
            if not ln:
                continue
            try:
                d = json.loads(ln)
            except Exception:
                continue
            nm = d["name"].split(".")[-1]
            _stmt.setdefault(nm, f"Lemma {d['name']} : {d['type']}.")
    return _stmt


_DBQ = ("SELECT text FROM sentence WHERE text LIKE ? LIMIT 1")


def _from_db(name: str, db: str) -> Optional[str]:
    global _con
    if _con is None:
        try:
            _con = sqlite3.connect(db, check_same_thread=False)
            _con.execute("PRAGMA query_only=1")
        except Exception:
            _con = False
    if not _con:
        return None
    bare = name.split(".")[-1]
    for kw in ("Lemma", "Theorem", "Corollary", "Remark", "Proposition", "Definition"):
        for c in (":%", " %"):
            try:
                r = _con.execute(_DBQ, (f"{kw} {bare}{c}",)).fetchone()
            except Exception:
                return None
            if r:
                return r[0]
    return None


def prioritize(ranked: list, added_texts: set, top: Optional[int] = None) -> list:
    """Coq 이 **적용 가능하다고 검증한** 것을 앞으로 당긴다.

    ★ 그냥 풀에 넣기만 하면 랭커가 tf-idf 로 다시 줄 세우므로 묻힌다 —
      실측: 합집합만 하면 top-100 진입이 +4.1pp 에 그쳤다.
      그런데 이것들은 **`SearchPattern`/`SearchRewrite` 가 통과시킨 것**이라
      "닮았다"가 아니라 "**된다**"에 가깝다. `eqx` 커널이 exact 성공을 사전식
      분리자로 인코딩한 것과 같은 논리다(experiment.txt §36-4).

    ★★ **그런데 실측은 반대였다 — 기본을 `False` 로 둔다.**

        PRIORITY_TOP   풀/top100      프롬프트
             0 (끔)      +5.4pp        **+0.9pp**
             8           +4.5pp         -0.9pp
            20           +4.5pp         -4.5pp

      프롬프트 예산에 들어가는 premise 는 **~25개**뿐인데, 검증된 것을 앞세우면
      그만큼 tf-idf 상위를 **밀어낸다**. Coq 이 통과시킨 것이 곧 gold 인 것은 아니고
      (질의가 넓으면 수백 개가 나온다) 평균적으로 손해다.
      → 풀에 **합치기만** 하고 순위는 랭커에 맡긴다.
    """
    if not PRIORITIZE or not added_texts:
        return ranked
    top = PRIORITY_TOP if top is None else top
    head, tail = [], []
    for p_ in ranked:
        t = getattr(p_, "text", "") or ""
        (head if (t in added_texts and len(head) < top) else tail).append(p_)
    return head + tail


def as_sentences(texts: list, file_path: str = "<coq-search>") -> list:
    """텍스트를 `Sentence` 로 감싼다 — 랭커·필터가 그 타입을 기대한다.

    `sentence_type` 은 `THEOREM` 으로 둔다(제외 규칙에 안 걸리게).
    `db_idx=None` 이라 DB 에 안 들어간다 — 런타임 전용이다.
    """
    from data_management.dataset_file import Sentence, TermType
    out = []
    for t in texts:
        try:
            out.append(Sentence(text=t, file_path=file_path, module=[],
                                sentence_type=TermType.THEOREM, line=0, db_idx=None))
        except Exception:
            pass
    return out


def extra(key, sentence_db: str = "", have: Optional[set] = None) -> list:
    """이 스텝에 **합칠 premise 텍스트**. 없으면 빈 목록.

    `have` 에 이미 풀에 있는 이름을 주면 중복을 뺀다.
    """
    if not ENABLED:
        return []
    with _lock:
        names = list(_found.get(key) or [])
    if not names:
        return []
    idx = _index()
    have = have or set()
    out = []
    for n in names:
        b = n.split(".")[-1]
        if b in have or n in have:
            continue
        t = idx.get(b) or (_from_db(n, sentence_db) if sentence_db else None)
        if t:
            out.append(t)
        if len(out) >= MAX_ADD:
            break
    return out
