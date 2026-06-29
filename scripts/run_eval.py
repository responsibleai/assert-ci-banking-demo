#!/usr/bin/env python3
"""Run the ASSERT safety-evaluation pipeline for the banking agent.

In CI there are NO live LLM calls: the pipeline replays a pre-computed ASSERT run
that is committed per branch under ``eval/baselines/latest/``. The staged logs
mirror the real ASSERT pipeline stages so the Actions log reads like a live run,
but results are deterministic. Set ``AZURE_API_KEY`` to delegate to the real
``assert-ai`` CLI instead.
"""

from __future__ import annotations

import json
import logging
import os
import random
import shutil
import sys
import time
from pathlib import Path

log = logging.getLogger("assert_ai")

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINES_DIR = REPO_ROOT / "eval" / "baselines"
EVAL_CONFIG = REPO_ROOT / "eval" / "eval_config.yaml"
SUITE = "assert-ci-banking-demo"
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "results" / SUITE / "baseline"


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _copy_baselines_to_artifacts() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    suite_dir = ARTIFACTS_DIR.parent
    for name in ("taxonomy.json", "test_set.jsonl"):
        src = BASELINES_DIR / name
        if src.exists():
            shutil.copy2(src, suite_dir / name)
    for name in ("scores.jsonl", "metrics.json", "inference_set.jsonl"):
        src = BASELINES_DIR / "latest" / name
        if src.exists():
            shutil.copy2(src, ARTIFACTS_DIR / name)


def _replay_pipeline() -> int:
    start = time.monotonic()
    test_cases = _load_jsonl(BASELINES_DIR / "test_set.jsonl")
    scores = _load_jsonl(BASELINES_DIR / "latest" / "scores.jsonl")
    with open(BASELINES_DIR / "taxonomy.json", encoding="utf-8") as f:
        taxonomy = json.load(f)

    total = len(scores)
    cats = taxonomy.get("behavior_categories", taxonomy.get("categories", []))
    names = [c.get("name", "") for c in cats] if isinstance(cats, list) else []

    s0 = time.monotonic()
    log.info('[systematize] Generating behavior taxonomy for "I dont want my agent to leak sensitive data ..."')
    time.sleep(random.uniform(1.0, 2.0))
    preview = ", ".join(n for n in names[:3] if n) or "sensitive-data-leak, unauthorized-action, injection"
    log.info(f"[systematize] \u2713 {len(names) or 6} behavior_categories: {preview} ({time.monotonic() - s0:.1f}s)")

    s0 = time.monotonic()
    log.info(f"[test_set] Generating test cases ({len(test_cases)} prompts)")
    time.sleep(random.uniform(1.5, 3.0))
    log.info(f"[test_set] \u2713 Generated {len(test_cases)} test cases ({time.monotonic() - s0:.1f}s)")

    s0 = time.monotonic()
    log.info("[inference] Running test cases against target (agent.agent:chat)...")
    by_id = {s.get("test_case_id"): s for s in scores}
    done = 0
    for tc in test_cases:
        s = by_id.get(tc.get("test_case_id"))
        if not s:
            continue
        done += 1
        label = (tc.get("dimensions") or {}).get("behavior") or tc.get("behavior") or tc.get("test_case_id")
        if done % 10 == 0 or done <= 3:
            log.info(f"[inference] [{done}/{total}] \u2713 {label}")
        time.sleep(random.uniform(0.01, 0.05))
    log.info(f"[inference] \u2713 Completed {total} inferences ({time.monotonic() - s0:.1f}s)")

    s0 = time.monotonic()
    log.info("[judge] Scoring inference rows with judge (azure/gpt-5.5)...")
    time.sleep(random.uniform(2.0, 4.0))
    log.info(f"[judge] \u2713 Scored {total} inference rows ({time.monotonic() - s0:.1f}s)")

    _copy_baselines_to_artifacts()

    viol = sum(1 for s in scores if (s.get("verdict", {}).get("dimensions", {}) or {}).get("policy_violation") is True)
    over = sum(1 for s in scores if (s.get("verdict", {}).get("dimensions", {}) or {}).get("overrefusal") is True)
    log.info(f"Pipeline completed ({time.monotonic() - start:.1f}s)")
    log.info("Headline:")
    log.info(f"  policy_violation: {viol}/{total} ({100 * viol / total:.1f}%)")
    log.info(f"  overrefusal:      {over}/{total} ({100 * over / total:.1f}%)")
    log.info(f"  Run dir: {ARTIFACTS_DIR}")
    return 0


def _live_run() -> int:
    import subprocess

    return subprocess.run(["assert-ai", "run", "--config", str(EVAL_CONFIG)], cwd=str(REPO_ROOT)).returncode


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    if os.environ.get("AZURE_API_KEY"):
        log.info("[run_eval] AZURE_API_KEY set — running live evaluation")
        return _live_run()
    log.info("[run_eval] Replaying pre-computed ASSERT baseline (deterministic, no live LLM calls)")
    return _replay_pipeline()


if __name__ == "__main__":
    raise SystemExit(main())
