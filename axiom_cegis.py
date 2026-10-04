#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Candidate:
    name: str
    cost: int

    def eval(self, x: int) -> int:
        if self.name == "x":
            return x
        if self.name == "neg-x":
            return -x
        if self.name == "zero":
            return 0
        if self.name == "abs-branch":
            return -x if x < 0 else x
        raise ValueError(self.name)

    def program(self, module: str) -> str:
        code = {
            "x": ["LOAD_INPUT r0 x", "RETURN r0"],
            "neg-x": ["LOAD_INPUT r0 x", "NEG r1 r0", "RETURN r1"],
            "zero": ["CONST r0 0", "RETURN r0"],
            "abs-branch": [
                "LOAD_INPUT r0 x",
                "NEG r1 r0",
                "SELECT_NEG_INPUT r2 x r1 r0",
                "RETURN r2",
            ],
        }[self.name]
        return (
            "AXIOM-PROGRAM/2\n"
            f"module={module}\n"
            "inputs=x\n"
            "output=result\n"
            "capabilities=\n"
            f"source.expr={self.name}\n"
            "code:\n"
            + "\n".join(code)
            + "\nend\n"
        )


def load_symbolic(path: Path):
    spec = importlib.util.spec_from_file_location("axiom_symbolic_external", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load verifier from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_spec(raw: str) -> dict[str, str]:
    lines = raw.splitlines()
    if not lines or lines[0] != "AXIOM-IR/2":
        raise ValueError("expected AXIOM-IR/2")
    return dict(line.split("=", 1) for line in lines[1:] if "=" in line)


def expected_abs(x: int) -> int:
    # v0.2 CEGIS demo intentionally targets the canonical abs specification.
    return abs(x)


def choose_candidate(examples: list[int]) -> Candidate:
    candidates = [
        Candidate("x", 1),
        Candidate("neg-x", 2),
        Candidate("zero", 1),
        Candidate("abs-branch", 4),
    ]
    candidates.sort(key=lambda item: item.cost)
    for candidate in candidates:
        if all(candidate.eval(x) == expected_abs(x) for x in examples):
            return candidate
    raise RuntimeError("grammar contains no candidate consistent with examples")


def emit_history(history: list[dict[str, str]]) -> str:
    out = ["AXIOM-CEGIS-HISTORY/1"]
    for index, item in enumerate(history):
        out.append(f"iteration.{index}.candidate={item['candidate']}")
        out.append(f"iteration.{index}.candidate.sha256={item['candidate.sha256']}")
        out.append(f"iteration.{index}.verdict={item['verdict']}")
        out.append(f"iteration.{index}.counterexample={item['counterexample']}")
    return "\n".join(out) + "\n"


def run(args: argparse.Namespace) -> int:
    verifier = load_symbolic(Path(args.verifier))
    spec_raw = Path(args.spec).read_text()
    spec = parse_spec(spec_raw)
    module = spec["module"]

    examples = [0]
    history: list[dict[str, str]] = []
    final_program = None
    final_proof = None

    for iteration in range(args.max_iterations):
        candidate = choose_candidate(examples)
        program_raw = candidate.program(module)
        valid, meta, cex = verifier.verify(spec_raw, program_raw)
        proof_raw = verifier.emit_proof(spec_raw, program_raw, valid, meta, cex)
        candidate_hash = hashlib.sha256(program_raw.encode()).hexdigest()
        history.append(
            {
                "candidate": candidate.name,
                "candidate.sha256": candidate_hash,
                "verdict": "VALID" if valid else "INVALID",
                "counterexample": "none" if cex is None else cex["input.x"],
            }
        )
        print(
            f"iteration {iteration}: candidate={candidate.name} examples={examples} "
            f"verdict={'VALID' if valid else 'INVALID'}"
        )
        if valid:
            final_program = program_raw
            final_proof = proof_raw
            break
        assert cex is not None
        x = int(cex["input.x"])
        if x in examples:
            raise RuntimeError("verifier returned a repeated counterexample; synthesis is stuck")
        examples.append(x)
    else:
        raise RuntimeError("CEGIS iteration limit reached")

    Path(args.program).write_text(final_program)
    Path(args.proof).write_text(final_proof)
    Path(args.history).write_text(emit_history(history))
    print(f"converged after {len(history)} iteration(s); universal symbolic proof obtained")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec")
    parser.add_argument("--verifier", required=True)
    parser.add_argument("--program", required=True)
    parser.add_argument("--proof", required=True)
    parser.add_argument("--history", required=True)
    parser.add_argument("--max-iterations", type=int, default=8)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
