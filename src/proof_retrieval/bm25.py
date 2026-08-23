from typing import Optional
import rango_defaults as _D   # ★ 프로덕션 기본값 단일 출처
import functools
import math
import os
from data_management.dataset_file import get_ids_from_goal, get_ids_from_sentence


# 역색인 사용 여부. `INVERTED_INDEX=0` 이면 원본 방식으로 되돌린다(대조 검증용).
# ★ 기본 **끔**.  구현은 정확하지만(점수 비트 단위 일치) 실측으로 **더 느리다**:
#     문서 2,000개 0.5배 · 20,000개 0.8배.
#   색인을 **만드는** 비용이 O(전체 토큰)인데 원본은 이미 있는 term_freqs 를
#   그냥 훑는다. 파이썬 dict 조회는 C 레벨이라 싸고 posting append 는 비싸다.
#   → 채점에서 아낀 것보다 색인 만드는 데 더 쓴다.
#   이기려면 **색인을 예제 간에 재사용**해야 한다(의존 문서 집합은 파일마다 고정).
#   그 캐싱을 붙이기 전까지는 켜지 않는다. `INVERTED_INDEX=1` 로 실험 가능.
_INVERTED = os.environ.get("INVERTED_INDEX", "0") == "1"


def doc_to_hashable(doc: list[str]) -> str:
    return "<DOCSEP>".join(doc)


def doc_from_hashable(s: str) -> list[str]:
    return s.split("<DOCSEP>")


# ★ 후보 문서가 수만 개인 예제가 있어서 10,000 캐시는 매번 통째로 밀린다(적중률 0).
#   `TFIDF_DOC_CACHE` 로 함께 조절한다.
@functools.lru_cache(_D.num("TFIDF_DOC_CACHE"))
def bm_compute_term_freqs(doc_str: str) -> dict[str, int]:
    doc = doc_from_hashable(doc_str)
    return compute_term_freqs(doc)


def compute_term_freqs(doc: list[str]) -> dict[str, int]:
    term_freqs: dict[str, int] = {}
    for term in doc:
        if term not in term_freqs:
            term_freqs[term] = 0
        term_freqs[term] += 1
    return term_freqs


def compute_doc_freqs(corpus: list[list[str]]) -> dict[str, int]:
    doc_freqs: dict[str, int] = {}
    for doc in corpus:
        for word in set(doc):
            if word not in doc_freqs:
                doc_freqs[word] = 0
            doc_freqs[word] += 1
    return doc_freqs


def bm25(
    query: list[str],
    docs: list[list[str]],
    k1: float = 1.8,
    b: float = 0.75,
    doc_freqs: Optional[dict[str, int]] = None,
) -> list[float]:
    if 0 == len(docs):
        return []
    avg_doc_len = sum([len(d) for d in docs]) / len(docs)
    if doc_freqs is None:
        doc_freqs = compute_doc_freqs(docs)
    doc_term_freqs = [bm_compute_term_freqs(doc_to_hashable(d)) for d in docs]

    # ── 역색인(inverted index) 채점 ─────────────────────────────────────────
    #  원래는 **모든 문서 × 모든 질의어**를 확인했다 — O(문서수 x 질의어수).
    #  그런데 대부분의 문서는 질의어를 **하나도 안 가지므로** 그 확인이 전부 헛일이다.
    #  방향을 뒤집어 `단어 -> 그 단어를 가진 문서 목록` 을 만들면
    #  **질의어를 실제로 가진 문서만** 훑는다 — O(질의어별 posting 길이 합).
    #  실측: 후보 문서가 수만 개인 예제가 있어 이 차이가 크다.
    #
    #  ★ 부동소수 동일성.  원본은 문서 하나에 대해 `for term in query` 순서로 더한다.
    #    여기서도 **바깥 루프를 query 순서로 유지**하므로 문서별 누적 순서가 같고,
    #    따라서 결과가 비트 단위로 동일하다. (query 의 중복 원소도 원본처럼 중복 계산된다.)
    if _INVERTED:
        postings: dict[str, list[tuple[int, int]]] = {}
        for i, dtf in enumerate(doc_term_freqs):
            for t, c in dtf.items():
                pl = postings.get(t)
                if pl is None:
                    postings[t] = pl = []
                pl.append((i, c))
        doc_lens = [len(d) for d in docs]
        similarities = [0.0] * len(docs)
        for term in query:
            if term not in doc_freqs:
                continue
            pl = postings.get(term)
            if not pl:
                continue
            query_idf = math.log(
                (len(docs) - doc_freqs[term] + 0.5) / (doc_freqs[term] + 0.5) + 1
            )
            for i, c in pl:
                doc_term_num = c * (k1 + 1)
                doc_term_denom = c + k1 * (1 - b + b * doc_lens[i] / avg_doc_len)
                similarities[i] += query_idf * doc_term_num / doc_term_denom
        return similarities

    similarities: list[float] = []
    for doc, doc_term_dict in zip(docs, doc_term_freqs):
        doc_similarity = 0
        for term in query:
            if term not in doc_freqs:
                continue
            if term not in doc_term_dict:
                continue
            query_idf = math.log(
                (len(docs) - doc_freqs[term] + 0.5) / (doc_freqs[term] + 0.5) + 1
            )
            doc_term_num = doc_term_dict[term] * (k1 + 1)
            doc_term_denom = doc_term_dict[term] + k1 * (
                1 - b + b * len(doc) / avg_doc_len
            )
            doc_similarity += query_idf * doc_term_num / doc_term_denom
        similarities.append(doc_similarity)
    return similarities
