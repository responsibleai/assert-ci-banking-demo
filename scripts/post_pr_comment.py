#!/usr/bin/env python3
"""Post the ASSERT safety **decision-gate** summary as a PR comment.

Reads the gate report written by ``scripts/gate_eval.py``
(``artifacts/results/<suite>/gate_report.json``) and upserts a markdown summary
on the PR: the pass/fail decision and the per-axis baseline-vs-current table
(Delta pp, p-value, verdict) measured against the unguarded production baseline.

Env: PR_NUMBER, GH_TOKEN (pull-requests:write), GITHUB_REPOSITORY.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

MARKER = "<!-- ai-safety-eval-summary -->"
REPO_ROOT = Path(__file__).resolve().parent.parent
SUITE = "assert-ci-banking-demo"
REPORT_PATH = REPO_ROOT / "artifacts" / "results" / SUITE / "gate_report.json"

_ICON = {"Improved": "\u2705", "Regressed": "\u274c", "Inconclusive": "\u26a0\ufe0f"}


def format_comment(report: dict) -> str:
    passed = report["decision"] == "PASS"
    out = [MARKER, "## \U0001f6e1\ufe0f ASSERT \u2014 safety decision gate", ""]
    if passed:
        out += [
            "> [!TIP]",
            "> **Result: \u2705 PASS** \u2014 this change significantly improves the primary "
            "safety axis versus the unguarded production baseline, with no regression.",
        ]
    else:
        out += [
            "> [!CAUTION]",
            "> **Result: \u274c FAIL** \u2014 this change does not demonstrably improve safety "
            "over the unguarded production baseline (or it regresses a guarded axis). Merge blocked.",
        ]
    out += [
        "",
        "| Axis | Baseline (unguarded) | This change | \u0394 pp | p-value | Verdict |",
        "|:--|--:|--:|--:|--:|:--|",
    ]
    for r in report["axes"]:
        out.append(
            f"| `{r['axis']}` | {r['baseline_rate'] * 100:.0f}% | {r['current_rate'] * 100:.0f}% | "
            f"{r['delta_pp']:+.1f} | {r['p_value']:.3f} | {_ICON.get(r['verdict'], '')} {r['verdict']} |"
        )
    out += [
        "",
        f"n={report['n_paired_cases']} paired test cases \u00b7 \u03b1={report['alpha']} "
        f"(Holm-Bonferroni across {len(report['axes'])} axes) \u00b7 judge azure/gpt-5.5 (replayed) "
        "\u00b7 baseline = unguarded production agent",
        "",
        f"<sub>**Rule** \u2014 {report['rule']}. `policy_violation` must *significantly improve*; "
        "`overrefusal` must not regress. A prompt tweak that only trends worse without a significant "
        "improvement does not clear the bar; a structural control plane that moves both axes does. "
        "Full report: `gate_report.json` in this run's artifacts.</sub>",
    ]
    return "\n".join(out)


def github_api(method: str, endpoint: str, data: dict | None = None) -> dict:
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GH_TOKEN"]
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}{endpoint}",
        data=json.dumps(data).encode() if data else None,
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
        method=method,
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main() -> None:
    pr = os.environ.get("PR_NUMBER")
    if not pr:
        print("PR_NUMBER not set, skipping comment")
        sys.exit(0)
    if not REPORT_PATH.exists():
        print(f"No gate report at {REPORT_PATH}, skipping comment")
        sys.exit(0)
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    body = format_comment(report)

    existing = github_api("GET", f"/issues/{pr}/comments")
    marker_id = next((c["id"] for c in existing if MARKER in c.get("body", "")), None)
    if marker_id:
        github_api("PATCH", f"/issues/comments/{marker_id}", {"body": body})
        print(f"Updated eval summary on PR #{pr}")
    else:
        github_api("POST", f"/issues/{pr}/comments", {"body": body})
        print(f"Posted eval summary to PR #{pr}")


if __name__ == "__main__":
    main()
