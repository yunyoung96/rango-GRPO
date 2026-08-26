# v9 문서

v9 가 모델에게 **무엇을 보여 주고 무엇을 안 보여 주는가**, 그리고 모델이 그것으로
**무엇을 만들어 내는가**를 다루는 곳. 설정값 자체는 `src/rango_defaults.py` 가
단일 출처이고, 여기는 그 설정이 만들어 내는 **내용**을 본다.

| 디렉토리 | 무엇 |
|---|---|
| [apply/](apply/) | `apply`·`rewrite` 의 형태 분포와, 그 형태를 내는 데 필요한데 프롬프트에 없는 정보 |
| [rewrite/](rewrite/) | `rewrite` 가 실패하는 이유 |
| [checkpoint25000/](checkpoint25000/) | 25k 오라클 실험(검색이냐 조립이냐) · `assert` 효용 분석 |
| [checkpoint47000/](checkpoint47000/) | 47k 재실험 — 더 학습하면 gold lemma 주입이 먹히는가 · gold 를 줘도 실패하는 이유 |
| [terms-and-results.md](terms-and-results.md) | 용어와 누적 결과 |

## 체크포인트별 요약

| 체크포인트 | 스텝 | train / eval loss | rand200 | 한 줄 |
|---|---|---|---|---|
| checkpoint-12000 | 12,000 (0.14 ep) | 0.5132 / 0.6289 | — | 프롬프트 불일치 수정 전 |
| [checkpoint-25000](checkpoint25000/experiment.md) | 25,000 (0.35 ep) | 0.4524 / 0.6088 | 30.0% | 병목은 조립이 아니라 **고르기** |
| [checkpoint-47000](checkpoint47000/experiment.md) | 47,000 (0.70 ep) | 0.4290 / 0.5818 | 측정 중 | loss 는 내려가는데 **능력은 25k 에서 포화** |
