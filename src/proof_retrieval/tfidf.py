from typing import Optional
import rango_defaults as _D   # ★ 프로덕션 기본값 단일 출처
import functools
import math
import os
import functools

from proof_retrieval.bm25 import (
    compute_term_freqs,
    compute_doc_freqs,
    doc_to_hashable,
    doc_from_hashable,
)


# ★ 기본 **끔**.  구현은 정확하지만(점수 비트 단위 일치) 실측으로 **더 느리다**:
#     문서 2,000개 0.5배 · 20,000개 0.8배.
#   색인을 **만드는** 비용이 O(전체 토큰)인데 원본은 이미 있는 term_freqs 를
#   그냥 훑는다. 파이썬 dict 조회는 C 레벨이라 싸고 posting append 는 비싸다.
#   → 채점에서 아낀 것보다 색인 만드는 데 더 쓴다.
#   이기려면 **색인을 예제 간에 재사용**해야 한다(의존 문서 집합은 파일마다 고정).
#   그 캐싱을 붙이기 전까지는 켜지 않는다. `INVERTED_INDEX=1` 로 실험 가능.
_INVERTED = os.environ.get("INVERTED_INDEX", "0") == "1"


def compute_idfs(corpus: list[list[str]]) -> dict[str, float]:
    if 0 == len(corpus):
        return {}
    assert 0 < len(corpus)
    doc_freqs = compute_doc_freqs(corpus)

    idfs: dict[str, float] = {}
    for k, v in doc_freqs.items():
        idfs[k] = math.log(len(corpus) / v)
    return idfs


# ★ 캐시 크기가 후보 문서 수보다 작으면 **매 예제마다 통째로 밀려** 적중률이 0 이 된다.
#   의존이 많은 파일은 후보 문서가 수만 개다(실측 최대 예제 하나에 280초).
#   `TFIDF_DOC_CACHE` 로 조절한다. 항목 하나는 작은 dict 라 10만개도 수백 MB 수준이다.
@functools.lru_cache(_D.num("TFIDF_DOC_CACHE"))
def compute_doc_tf(doc_str: str) -> dict[str, float]:
    doc = doc_from_hashable(doc_str)
    # doc = tokenize(premise)
    if 0 == len(doc):
        return {}
    assert 0 < len(doc)
    term_freqs = compute_term_freqs(doc)

    tfs: dict[str, float] = {}
    for k, v in term_freqs.items():
        tfs[k] = v / len(doc)
    return tfs


def compute_query_tf(query: list[str]) -> dict[str, float]:
    if 0 == len(query):
        return {}
    assert 0 < len(query)
    term_freqs: dict[str, int] = {}
    max_term_freq = 0
    for word in query:
        if word not in term_freqs:
            term_freqs[word] = 0
        term_freqs[word] += 1
        if max_term_freq < term_freqs[word]:
            max_term_freq = term_freqs[word]

    tfs: dict[str, float] = {}
    for k, v in term_freqs.items():
        tfs[k] = 0.5 + 0.5 * (v / max_term_freq)
    return tfs


def tf_idf(
    query: list[str], docs: list[list[str]], idfs: Optional[dict[str, float]] = None
) -> list[float]:
    if idfs is None:
        idfs = compute_idfs(docs)
    query_tfs = compute_query_tf(query)
    doc_tfs = [compute_doc_tf(doc_to_hashable(d)) for d in docs]

    # ── 역색인 채점 (bm25.py 와 같은 논리) ───────────────────────────────────
    #  원본은 모든 문서 × 모든 질의어를 확인한다. 대부분의 문서는 질의어를 안 가지므로
    #  헛일이다. `단어 -> 그 단어를 가진 문서` 로 뒤집어 필요한 것만 훑는다.
    #  ★ 바깥 루프를 `query_tfs` 순서로 유지 → 문서별 누적 순서가 원본과 같아
    #    부동소수 결과가 비트 단위로 동일하다.
    if _INVERTED:
        postings: dict[str, list[tuple[int, float]]] = {}
        for i, dtf in enumerate(doc_tfs):
            for t, v in dtf.items():
                pl = postings.get(t)
                if pl is None:
                    postings[t] = pl = []
                pl.append((i, v))
        similarities = [0.0] * len(docs)
        for term, query_tf in query_tfs.items():
            if term not in idfs:
                continue
            pl = postings.get(term)
            if not pl:
                continue
            idf = idfs[term]
            query_tf_idf = query_tf * idf
            for i, v in pl:
                similarities[i] += query_tf_idf * (v * idf)
        return similarities

    similarities: list[float] = []
    for doc_tf_dict in doc_tfs:
        dot_prod = 0
        for term, query_tf in query_tfs.items():
            if term not in doc_tf_dict:
                continue
            if term not in idfs:
                continue
            query_tf_idf = query_tf * idfs[term]
            doc_tf_idf = doc_tf_dict[term] * idfs[term]
            dot_prod += query_tf_idf * doc_tf_idf
        similarities.append(dot_prod)
    return similarities
