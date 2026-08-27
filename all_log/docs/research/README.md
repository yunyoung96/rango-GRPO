# 외부 조사 (research)

우리 코드베이스 **밖**을 뒤져서 얻은 것들. 논문·공식 저장소·아티팩트·선행 연구.
안쪽 실험은 [../premise/](../premise/) · [../v9/](../v9/) · [../grpo/](../grpo/) 에 있다.

방법은 공통이다 — 다각도 병렬 검색 → 1차 출처 fetch → 반증 가능한 주장으로 쪼갬 →
**3표 적대적 검증**(2/3 이상이 반증하면 기각) → 확인/기각/미검증으로 분류.
**기각된 주장도 남긴다** — 같은 생각이 다시 떠올랐을 때 되풀이하지 않으려고.

| 문서 | 질문 | 결론 |
|---|---|---|
| [train-dataset-recovery.md](train-dataset-recovery.md) | TRAIN 원본 `.v` 를 복구할 방법이 있나 | **있다.** `splits/commits.json` 이 열쇠 — 실제로 96.1% 복구(13GB) |
| [classical-lemma-retrieval.md](classical-lemma-retrieval.md) | `rewrite`/`apply` 할 lemma 를 찾는 고전(비-LLM) 연구가 있나 | **있다.** 두 갈래 — 관련성 랭킹(TF-IDF·MePo·MaSh) 과 **적용가능성 색인**(지문/판별트리). 우리 문제는 후자인데 전자 도구로 풀고 있다 |
| [applicability-filter.md](applicability-filter.md) | 적용가능성으로 먼저 거르고 점수를 매기면 gold 가 더 실리나 | **음성 (8판본 · 색인 4종).** 양쪽 elaborate 후에도 판별트리 45.1% / 치환트리 44.7% / 지문 47.6% (축소 5.7배), 깊이 0 은 88.2% / 2.6배. 남은 벽은 **변환(delta/iota)**. → **Coq 내장 `SearchPattern`/`SearchRewrite`** 가 그걸 넘는다(질의 35ms·결과 6.9개). 구체→추상 사다리 필요 |
