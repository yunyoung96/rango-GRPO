from __future__ import annotations
import argparse
import os
import json
import ipdb
from enum import Enum
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Any

from coqstoq.check import Result
from coqstoq.eval_thms import EvalTheorem, get_file_hash, Position
from coqstoq import get_theorem_list, Split

from evaluation.translate import (
    raw_results_to_results,
    RawResult,
    get_save_loc,
    get_coqstoq_split,
    get_thm_hash,
    get_theorem_str,
    get_raw_file_set,
    get_coqstoq_files,
)

import logging


META_IDX = 0
META_PROJ_IDX = 0
META_FILE_IDX = 1
META_MODULE_IDX = 2
META_THM_IDX = 3

PROOF_IDX = 1


def proof_from_cmds(commands: list[Any]) -> str:
    tactics = [c["tactic"] for c in commands]
    return "\n".join(tactics)


def from_json(json_data: Any) -> RawResult:
    metadata_json = json_data[META_IDX]
    proj = metadata_json[META_PROJ_IDX]
    file = metadata_json[META_FILE_IDX]
    thm = metadata_json[META_THM_IDX]
    module = metadata_json[META_MODULE_IDX]
    assert 0 < len(module) and module.endswith(".")
    module_list_w_filename = module[:-1].split(".")
    assert 0 < len(module_list_w_filename)
    module_list = module_list_w_filename[1:]

    proof_json = json_data[PROOF_IDX]
    success = proof_json["status"] == "SUCCESS"
    if (
        not success
        and proof_json["status"] != "INCOMPLETE"
        and proof_json["status"] != "FAILURE"
        and proof_json["status"] != "CRASHED"
    ):
        print(json.dumps(json_data, indent=2))
        exit()
    proof = proof_from_cmds(proof_json["commands"]) if success else None

    time = proof_json["time_taken"]
    return RawResult(proj, file, thm, success, time, proof)


def results_from_file(file_path: Path) -> list[RawResult]:
    file_results: list[RawResult] = []
    with file_path.open() as fin:
        for line in fin:
            line_info = json.loads(line)
            file_results.append(from_json(line_info))
    return file_results


def load_proverbot_results(path: Path) -> list[RawResult]:
    results: list[RawResult] = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith("proofs.txt"):
                results.extend(results_from_file(Path(root) / file))
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--proverbot_loc", type=str, required=True)
    parser.add_argument("--coqstoq_loc", type=str, required=True)
    parser.add_argument(
        "--split", type=str, required=True, choices=["val", "test", "cutoff"]
    )
    parser.add_argument("--save_loc", type=str, required=True)

    args = parser.parse_args()
    proverbot_results = load_proverbot_results(Path(args.proverbot_loc))
    split = get_coqstoq_split(args.split)
    results = raw_results_to_results(proverbot_results, Path(args.coqstoq_loc), split)

    # Save results
    for r in results:
        save_loc = get_save_loc(Path(args.save_loc), r.thm)
        os.makedirs(save_loc.parent, exist_ok=True)
        with save_loc.open("w") as fout:
            json.dump(r.to_json(), fout, indent=2)

    print("Num not none", len(results))
    result_thms = set([get_thm_hash(r.thm) for r in results])
    print("Set size", len(result_thms))

    # find missing
    coqstoq_files = get_coqstoq_files(Path(args.coqstoq_loc), split)
    thms = get_theorem_list(split, Path(args.coqstoq_loc))
    print("Num coqstoq theorems", len(thms))
    proverbot_files = get_raw_file_set(proverbot_results)
    because_file_missing = 0
    total = 0
    missing_files: set[Path] = set()
    for t in thms:
        if get_thm_hash(t) not in result_thms:
            thm_path = Path(t.project.workspace.name) / t.path
            if thm_path not in proverbot_files:
                because_file_missing += 1
                missing_files.add(thm_path)
            total += 1
            print("File", thm_path)
            print(get_theorem_str(t, coqstoq_files[thm_path]))
            print()

    print("Because file missing", because_file_missing)
    print("Missing", total)
    for f in sorted(list(missing_files)):
        print(f)
