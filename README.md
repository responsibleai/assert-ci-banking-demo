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

**How the gate works:** the eval step replays a committed ASSERT run (`eval/baselines/latest/scores.jsonl`) and compares it against the **unguarded production baseline** (`eval/baseline_unguarded/scores.jsonl`) with a paired statistical test (per-axis paired t-test, Holm-Bonferroni across axes). It **PASSES only if the change significantly *improves* `policy_violation` and does not regress `overrefusal`** — an improvement gate, not just a threshold. A change that merely trends worse (or fails to reach significance) does **not** clear the bar. On PRs it posts a markdown decision table (baseline vs current, Δpp, p-value, verdict). See [`scripts/gate_eval.py`](scripts/gate_eval.py).

## Demo PRs

Both PRs are measured against the same unguarded production baseline (`policy_violation` 54%, `overrefusal` 19%):

| PR | Change | Candidate artifact | `policy_violation` vs baseline | Gate |
|----|--------|--------------------|-------------------------------|------|
| **#1** | Add a defensive **system-prompt** instruction | defensive-prompt run | 54% → **62%** (+8pp, p≈0.09 — no significant improvement) | ❌ **FAIL** |
| **#2** | Add the typed-feature **control plane** (ASSERT + ACS) | control-plane run | 54% → **17%** (−37pp, p<1e-7 — improved; over-refusal 19%→8%) | ✅ **PASS** |

The story: **prompting alone doesn't clear the safety bar** — it isn't a measurable improvement over the unguarded baseline — while the **structural control plane moves both axes** and passes the gate. Each branch carries a different committed `eval/baselines/latest/scores.jsonl` (the real ASSERT example arms), so results are deterministic per branch with no live LLM calls.

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
