from typing import Any


from model_deployment.proof_manager import ProofManager
from model_deployment.tactic_gen_client import TacticGenClient
from model_deployment.classical_searcher import (
    ClassicalSearchConf,
    ClassicalSearcher,
    ClassicalSuccess,
    ClassicalFailure,
)
from model_deployment.straight_line_searcher import (
    StraightLineSearcherConf,
    StraightLineSearcher,
    StraightLineSuccess,
    StraightLineFailure,
)
from model_deployment.whole_proof_searcher import (
    WholeProofSearcherConf,
    WholeProofSearcher,
    WholeProofSuccess,
    WholeProofFailure,
)
from model_deployment.portfolio_searcher import (
    PortfolioSearchConf,
    PortfolioSearcher,
)
from model_deployment.rmaxts_searcher import (
    RMaxTSSearchConf,
    RMaxTSSearcher,
)
from model_deployment.bfs_prover_searcher import (
    BFSProverSearchConf,
    BFSProverSearcher,
)
from model_deployment.quarry_searcher import (
    QuarrySearchConf,
    QuarrySearcher,
)
from model_deployment.pgts_searcher import (
    PGTSSearchConf,
    PGTSSearcher,
)
from model_deployment.progress_searcher import (
    ProgressSearchConf,
    ProgressSearcher,
)
from tactic_gen.grpo_rollout import (
    GRPORolloutSearchConf,
    GRPORolloutSearcher,
)

SuccessfulSearch = ClassicalSuccess | StraightLineSuccess | WholeProofSuccess
FailedSearch = ClassicalFailure | StraightLineFailure | WholeProofFailure
SearchResult = SuccessfulSearch | FailedSearch

Searcher = ClassicalSearcher | StraightLineSearcher | WholeProofSearcher | PortfolioSearcher | RMaxTSSearcher | BFSProverSearcher | QuarrySearcher | PGTSSearcher | ProgressSearcher | GRPORolloutSearcher
SearcherConf = (
    ClassicalSearchConf
    | StraightLineSearcherConf
    | WholeProofSearcherConf
    | PortfolioSearchConf
    | RMaxTSSearchConf
    | BFSProverSearchConf
    | QuarrySearchConf
    | PGTSSearchConf
    | ProgressSearchConf
    | GRPORolloutSearchConf
)


def searcher_conf_from_yaml(yaml_data: Any) -> SearcherConf:
    attempted_alias = yaml_data["alias"]
    match attempted_alias:
        case ClassicalSearchConf.ALIAS:
            return ClassicalSearchConf.from_yaml(yaml_data)
        case StraightLineSearcherConf.ALIAS:
            return StraightLineSearcherConf.from_yaml(yaml_data)
        case WholeProofSearcherConf.ALIAS:
            return WholeProofSearcherConf.from_yaml(yaml_data)
        case PortfolioSearchConf.ALIAS:
            return PortfolioSearchConf.from_yaml(yaml_data)
        case RMaxTSSearchConf.ALIAS:
            return RMaxTSSearchConf.from_yaml(yaml_data)
        case BFSProverSearchConf.ALIAS:
            return BFSProverSearchConf.from_yaml(yaml_data)
        case QuarrySearchConf.ALIAS:
            return QuarrySearchConf.from_yaml(yaml_data)
        case PGTSSearchConf.ALIAS:
            return PGTSSearchConf.from_yaml(yaml_data)
        case ProgressSearchConf.ALIAS:
            return ProgressSearchConf.from_yaml(yaml_data)
        case GRPORolloutSearchConf.ALIAS:
            return GRPORolloutSearchConf.from_yaml(yaml_data)
        case _:
            raise ValueError("Searcher not found.")


def searcher_from_conf(
    conf: SearcherConf, tactic_gens: list[TacticGenClient], manager: ProofManager
) -> Searcher:
    match conf:
        case ClassicalSearchConf():
            return ClassicalSearcher.from_conf(conf, tactic_gens, manager)
        case StraightLineSearcherConf():
            return StraightLineSearcher.from_conf(conf, tactic_gens, manager)
        case WholeProofSearcherConf():
            return WholeProofSearcher.from_conf(conf, tactic_gens, manager)
        case PortfolioSearchConf():
            return PortfolioSearcher.from_conf(conf, tactic_gens, manager)
        case RMaxTSSearchConf():
            return RMaxTSSearcher.from_conf(conf, tactic_gens, manager)
        case BFSProverSearchConf():
            return BFSProverSearcher.from_conf(conf, tactic_gens, manager)
        case QuarrySearchConf():
            return QuarrySearcher.from_conf(conf, tactic_gens, manager)
        case PGTSSearchConf():
            return PGTSSearcher.from_conf(conf, tactic_gens, manager)
        case ProgressSearchConf():
            return ProgressSearcher.from_conf(conf, tactic_gens, manager)
        case GRPORolloutSearchConf():
            return GRPORolloutSearcher.from_conf(conf, tactic_gens, manager)
