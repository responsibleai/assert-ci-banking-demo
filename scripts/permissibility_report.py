#!/usr/bin/env python3
"""Report the permissibility split for a completed ASSERT run.

ASSERT splits a policy violation by the permissibility of the behavior that was
violated:

    policy_violation_not_permissible -> impermissible behavior violated
    policy_violation_permissible     -> permissible behavior violated

`policy_violation` unions the two, and `overrefusal` covers only the
refusal-shaped subset of the permissible half, so neither answers "did the agent
do something it must never do?" on its own.

The split is *derived*, not judged: it is computed from `verdict.node_judgments`
plus the run's behavior taxonomy, which is why an old run can be recalculated
without re-judging. It is also why the CI gate cannot currently act on it -- the
paired test runs per judged dimension, and this never reaches `scores.jsonl` as
one.

So: read it here.

    python scripts/permissibility_report.py artifacts/
    python scripts/permissibility_report.py path/to/downloaded-ci-artifacts/
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def load_taxonomy_flags(run_dir: Path) -> dict[str, bool]:
    """Map behavior-category name -> permissible flag, from the nearest taxonomy."""
    for parent in [run_dir, *run_dir.parents]:
        taxonomy = parent / "taxonomy.json"
        if taxonomy.is_file():
            data = json.loads(taxonomy.read_text(encoding="utf-8"))
            return {
                category.get("name"): category.get("permissible")
                for category in data.get("behavior_categories", [])
                if category.get("name") is not None
            }
    return {}


def summarize(scores: Path, flags: dict[str, bool]) -> Counter:
    counts: Counter = Counter()
    for line in scores.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        verdict = row.get("verdict") or {}
        dimensions = verdict.get("dimensions") or {}
        counts["n"] += 1
        counts["policy_violation"] += bool(dimensions.get("policy_violation"))
        counts["overrefusal"] += bool(dimensions.get("overrefusal"))

        impermissible = permissible = False
        for judgment in verdict.get("node_judgments") or []:
            if not judgment.get("violated"):
                continue
            flag = flags.get(judgment.get("node_name"))
            if flag is False:
                impermissible = True
            elif flag is True:
                permissible = True
        counts["not_permissible"] += impermissible
        counts["permissible"] += permissible
        counts["unclassified"] += (
            bool(dimensions.get("policy_violation")) and not (impermissible or permissible)
        )
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="artifacts root to scan for runs")
    args = parser.parse_args()

    if not args.root.is_dir():
        print(f"not a directory: {args.root}", file=sys.stderr)
        return 2

    runs = sorted(args.root.rglob("scores.jsonl"))
    if not runs:
        print(f"no scores.jsonl under {args.root}", file=sys.stderr)
        return 1

    exit_code = 0
    for scores in runs:
        flags = load_taxonomy_flags(scores.parent)
        counts = summarize(scores, flags)
        n = counts["n"] or 1

        # The behavior name is the artifacts-root directory the gate creates.
        try:
            label = scores.relative_to(args.root).parts[0]
        except ValueError:
            label = scores.parent.name

        print(f"\n{label}  (n={counts['n']})")
        if not flags:
            print("  no taxonomy.json found -- cannot split; showing the union only")
            print(f"  policy_violation (union)        {100 * counts['policy_violation'] / n:5.1f}%")
            exit_code = 1
            continue

        missing = sum(1 for value in flags.values() if value is None)
        if missing:
            print(f"  WARNING: {missing}/{len(flags)} categories lack a permissible flag")
            exit_code = 1

        print(f"  impermissible behavior violated {100 * counts['not_permissible'] / n:5.1f}%   <- headline")
        print(f"  permissible behavior violated   {100 * counts['permissible'] / n:5.1f}%")
        print(f"  [superseded] policy_violation   {100 * counts['policy_violation'] / n:5.1f}%")
        print(f"  [superseded] overrefusal        {100 * counts['overrefusal'] / n:5.1f}%")
        if counts["unclassified"]:
            # A violation whose node name is absent from the taxonomy lands in
            # neither half, so the two halves would not reconcile to the union.
            print(
                f"  unclassified violations         {counts['unclassified']}"
                "  (node name not found in the taxonomy)"
            )
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
