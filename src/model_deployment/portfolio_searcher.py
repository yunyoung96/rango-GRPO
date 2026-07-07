from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from model_deployment.proof_manager import ProofManager
from model_deployment.tactic_gen_client import TacticGenClient
from model_deployment.classical_searcher import (
    ClassicalSearchConf,
    ClassicalSearcher,
    ClassicalSuccess,
)
from model_deployment.straight_line_searcher import (
    StraightLineSearcherConf,
    StraightLineSearcher,
    StraightLineSuccess,
)


@dataclass
class PortfolioSearchConf:
    """Portfolio: straight-line을 timeout의 straight_frac만큼 먼저 돌리고,
    실패하면 남은 시간으로 classical(use_memo)을 돌린다. 두 방식이 상보적
    (straight-line ~11, classical이 idx27 등 별도 케이스)이라 union을 노림."""
    straight_conf: StraightLineSearcherConf
    classical_conf: ClassicalSearchConf
    timeout: int
    straight_frac: float = 0.7
    ALIAS = "portfolio"

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> "PortfolioSearchConf":
        return cls(
            StraightLineSearcherConf.from_yaml(yaml_data["straight"]),
            ClassicalSearchConf.from_yaml(yaml_data["classical"]),
            yaml_data["timeout"],
            yaml_data.get("straight_frac", 0.7),
        )


class PortfolioSearcher:
    def __init__(
        self,
        straight_conf: StraightLineSearcherConf,
        classical_conf: ClassicalSearchConf,
        timeout: int,
        straight_frac: float,
        tactic_gens: list[TacticGenClient],
        manager: ProofManager,
    ):
        self.straight_conf = straight_conf
        self.classical_conf = classical_conf
        self.timeout = timeout
        self.straight_frac = straight_frac
        self.tactic_gens = tactic_gens
        self.manager = manager

    @classmethod
    def from_conf(
        cls,
        conf: PortfolioSearchConf,
        tactic_gens: list[TacticGenClient],
        manager: ProofManager,
    ) -> "PortfolioSearcher":
        return cls(
            conf.straight_conf,
            conf.classical_conf,
            conf.timeout,
            conf.straight_frac,
            tactic_gens,
            manager,
        )

    def search(self, **kwargs):
        t1 = int(self.timeout * self.straight_frac)
        t2 = max(1, self.timeout - t1)
        # client 2개면 phase1=client0(plain), phase2=client1(sauto). 아니면 공용.
        gens1 = self.tactic_gens[:1] if len(self.tactic_gens) >= 2 else self.tactic_gens
        gens2 = self.tactic_gens[1:2] if len(self.tactic_gens) >= 2 else self.tactic_gens

        # phase 1: straight-line (강한 base, sauto 없음)
        self.straight_conf.timeout = t1
        print(f"\n[Portfolio] phase1 straight-line {t1}s")
        sl = StraightLineSearcher.from_conf(
            self.straight_conf, gens1, self.manager
        )
        r1 = sl.search(**kwargs)
        if isinstance(r1, StraightLineSuccess):
            print("[Portfolio] phase1 성공")
            return r1
        # phase 2: classical (memo) — sauto client이면 fallback으로 새 정리 획득
        self.classical_conf.timeout = t2
        print(f"\n[Portfolio] phase2 classical {t2}s")
        cl = ClassicalSearcher.from_conf(
            self.classical_conf, gens2, self.manager
        )
        return cl.search(**kwargs)
