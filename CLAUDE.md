# 작업 규칙

## 실험
- **실험을 설계·실행하기 전에 반드시 `all_log/docs/applicability/requirements.txt` 를 읽고, 모든 요구사항을 충족하도록 실험을 구성한다.** 요구사항 파일이 갱신될 수 있으니 매번 다시 읽는다.
- `all_log/docs/applicability/design_from_requirements.txt` 는 requirements.txt(특히 [B. sft])에 대한 **설계 답변**이다 — 요구사항이 갱신되면 답변도 함께 갱신하고, sft 관련 작업은 이 두 파일을 쌍으로 읽고 시작한다.
- 그외 계열 보고는 **외부참조 필요분만**(destruct·case·elim·induction) — unfold 는 프롬프트 [TYPES]/[DEFINITIONS] 가 커버하므로 제외하고 제외 수를 명시.
- 랭킹 보고는 split(TRAIN/VAL/TEST)별 · gold tactic 의 자기 채널 기준 @10/@20/@50, gold lemma 가 여러 개면 "하나라도 포함"과 "다 포함"을 구분해서 보여준다.
- 코드에 assert 를 많이 넣고(조용한 0 방지 — 판별 분기엔 양성 카운터), 합성 재현으로 동적 테스트를 하고, 장기 실행은 주기 모니터링을 붙인다.
- 알고리즘 설명은 `all_log/docs/applicability/versions/` 밑에 버전별로 정리한다.

## 환경
- opam/OCaml 버전 절대 변경 금지. 본학습은 다른 서버 — 여기선 스모크만.
- `all_log/docs/premise/experiment.txt` 는 append-only.
- 새 설정은 환경변수 말고 파이썬 모듈 상수 + 기본 인자로.
- 수집 회차 로그 명명: `r{플러그인버전}_v{회차}_{split}.log` (학습 v9/v10 과 구분).
- 산출물은 전부 .md (html/artifact 안 씀). 시간 보고는 KST.
