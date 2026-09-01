"""★ 익명화(정규화) 설정 — **파이썬 상수**다. 환경변수가 아니다.

## 왜 env 를 버렸나

예전에는 `PROD_DEFAULTS` 문자열 dict + `os.environ` 오버라이드였다. 두 번 당했다:

  · `NORMALIZE_INFERENCE=1` 을 전역 env 로 켜자 **학습 경로로 새어**,
    프롬프트는 익명인데 정답은 실명인 상태로 학습이 돌았다.
  · `RERANK_PREMISES` 가 꺼진 채 학습이 끝났는데, 결과만 보고는 설정이 빠진
    건지 알고리즘이 나쁜 건지 구분할 수 없었다.

셸 env 는 `source` 를 잊거나 다른 진입점으로 새면 **조용히** 다른 설정으로 돈다.
그래서 여기서는 값을 파이썬 상수로 못박고, 바꿔야 하면 **함수 기본인자**로만
받는다. 문자열 파싱도, 전역 오염도 없앤다.

## 값의 뜻

    NAMES         익명화 전체 스위치. 끄면 아래가 전부 무의미하다
    PREMISES      [PREMISES] 구간의 lemma 이름도 익명화 대상에 넣는다
    THEOREM       증명 중인 정리 이름도 대상
    LTAC          파일 내 Ltac 이름도 대상
    SKIP_STDLIB   stdlib 이름(13,819개)은 **익명화하지 않는다**
                  근거: Ltac 회상 61.5%(익명화 O) vs notation 53.5%(익명화 X)
                  — stdlib 은 모델이 이미 아는 어휘라 가리면 손해다
    RATE          이 비율만큼만 정규화한다(예제 key 해시로 결정적 선택).
                  1.0 = 전부. 학습에서 실명 경로를 남기려면 낮춘다
    INFERENCE     추론 프롬프트도 익명화한다(모델이 익명으로 학습됐으므로 기본 켬)
"""
from __future__ import annotations

# ── 값 (전부 파이썬 상수) ────────────────────────────────────────────────────
NAMES: bool = True
PREMISES: bool = True
THEOREM: bool = True
LTAC: bool = True
SKIP_STDLIB: bool = True
RATE: float = 1.0
INFERENCE: bool = True


def as_dict() -> dict:
    """지금 값 — 로그·리포트에 그대로 찍으라고 둔다."""
    return {"NAMES": NAMES, "PREMISES": PREMISES, "THEOREM": THEOREM,
            "LTAC": LTAC, "SKIP_STDLIB": SKIP_STDLIB, "RATE": RATE,
            "INFERENCE": INFERENCE}


def summary() -> str:
    return " · ".join(f"{k}={v}" for k, v in as_dict().items())
