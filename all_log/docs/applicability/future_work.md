# Future Work (applicability · SFT 계열)

기록일 2026-09-02. 지금 구현은 건드리지 않고, 다음에 캘 것들만 정리한다.

## 1. 변형(variant) 규칙 확장
규칙 후보의 단일 출처는 design_from_requirements.txt [3] "규칙표 v4 후보" 절로 이관 (2026-09-02).
구현 시 그 절을 '구현됨'으로 갱신할 것 (CLAUDE.md sync 규칙).

## 2. 증명기 내부 정보가 필요한 변형 (플러그인 확장)
설계표에 있었으나 미구현: `apply L with (x := t)` · `exact (L t₁ … tₙ)` 완전적용꼴 ·
`rewrite H at n / in ⋆`. probe_ok/verify 가 evar 해·출현 위치를 STAT 로 출력하면 구현 가능.

## 3. dec 채널 (아이디어 B)
그외-외부참조 실패의 31~48%가 stdlib 결정가능성 보조정리(…_dec, dec_…) — 전용 채널로 만들면
그외 @10 개선 여지 (r18.md 분석 참조).

## 4. 수집·데이터
- rw verify AllOccurrences 위음성 (TRAIN rewrite 회수 96.7→93.5 판) 재검.
- TEST math-classes 꼬리 수집(보고표 완성용 — 학습 아님. math-classes 는 TEST 저장소, C16 가드 유지).
- 빌드 캠페인 확장: 파일수 61위 이하 + "논리경로 불일치" 잔여(외부 라이브러리 의존 — opam 불변 제약과 상충, 보류).
- Core-Erlang Tests/ 류 병리 경로의 일반 감지(강제종료율 기반 자동 스킵).

## 5. 학습·추론
- 추론 프롬프트 빌더를 v2 물질화와 동일 형식(5블록 + [ErrorFeedback] 슬롯)으로 — 학습·추론 일치 (필수, ④ 이후).
- DPO 라운드 구현: milestone-5000 → (x−5000,x] 소비 예제 중 lemma 참조 · 균등 5,000 표본 × rollout 4 →
  Coq 3단 라벨(실패 ≺ 적용성공·gold 미사용 ≺ gold 사용) → DPO → 가중치 덮어쓰고 스케줄 재개.
- 2.5-Coder-3B 팔(같은 데이터)로 모델/데이터 효과 분리 (model_selection.txt).
- Qwen3.5-4B-Base 팔: 별도 venv(transformers 5.16+) + linear-attention 커널 빌드 필요 (2순위).
- decl_of DB 폴백: 한정자 모듈 일치 강제(Fin.case0 오해결 실측) 후 v11.1 재물질화
