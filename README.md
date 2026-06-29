# assert-ci-banking-demo

A banking agent with **[ASSERT](https://github.com/responsibleai/ASSERT)** wired into a CI/CD pipeline as an **AI safety regression gate**. Based on the ASSERT `bank_manager_agent_control` example.

> Private demo for the AIEWF talk. Pre-computed ASSERT artifacts only — **no live LLM calls in CI**, so every run is deterministic.

## The pipeline ([`.github/workflows/ci.yml`](.github/workflows/ci.yml))

Five jobs chained in sequence:

1. **Code Quality** — `ruff` lint + format checks
2. **Agent Unit Tests** — `pytest` suite for the agent's typed-feature gate
3. **AI Safety Regression** — runs the ASSERT evaluation suite; **this is the safety gate**
4. **Build & Package** — builds a Python wheel
5. **Deploy to Staging** — stages the wheel; only on merge to `master` (skipped on PRs / manual runs)

If the AI safety gate fails, **Build is skipped** and the PR is blocked. A run takes ~3–5 min.

**How the gate works:** the eval step replays a committed ASSERT run (`eval/baselines/latest/scores.jsonl`) and fails if the `policy_violation` rate exceeds **30%**. The control plane sits at ~17% (passes); the unguarded app at ~55% (fails). On PRs it posts a markdown report with pass/fail, per-dimension rates, and failing cases.

## Demo PRs

| PR | Change | Artifact | Gate |
|----|--------|----------|------|
| **PASS** | Expand safety directives into structured numbered rules | control-plane run (17%) | ✅ PASS |
| **FAIL** | Simplify agent system prompt | unguarded run (55%) | ❌ FAIL |

Each branch carries a different committed version of `eval/baselines/latest/scores.jsonl` (copied from the ASSERT example arms), so results are deterministic per branch.

## Manual runs

Trigger `Regression Tests` via **workflow_dispatch** against any branch; it runs the same eval but only posts a PR comment if you pass `post_to_pr`.

## Local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest -q
python scripts\run_eval.py
python scripts\gate_eval.py
```
