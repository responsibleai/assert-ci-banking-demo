# assert-ci-banking-demo

A customer-safe sandbox for running **[ASSERT](https://github.com/responsibleai/ASSERT)** against a live, intentionally imperfect retail-bank manager agent.

The agent is now a real **LangGraph** tool-using agent. It can look up accounts, clients, loans, brokerage records, policy snippets, and schedule transfers. Tool results carry a typed `risk_tier` signal (`standard`, `vip`, `high_net_worth`, `restricted`). The default agent is deliberately unguarded so ASSERT has real failures to find: it may disclose sensitive-tier records, schedule transfers without required approval, or invent unsupported policy.

## Wire this into your own repo

This repo is the worked example. To do the same thing to your own agent, paste this into your coding agent (Copilot CLI, Claude Code, or Cursor):

```text
read https://raw.githubusercontent.com/responsibleai/assert-action/main/ONBOARD.md
```

It detects how your agent is built, wraps it as an ASSERT target, extracts a draft spec for you to confirm or replace, splits it one behavior per YAML, runs a baseline, and wires the gate below.

## Agent entrypoint

ASSERT evaluates the callable target:

```text
agent.agent:chat
```

`chat(message: str, history: list[dict[str, str]] | None = None) -> str` enables OpenTelemetry auto-instrumentation at import time:

```python
from assert_ai import auto_trace

auto_trace.enable()
```

The eval configs use `target.callable` plus `target.trace` so the judge can inspect tool calls and routing, not just final text.

## BYO model credentials

There is no shared endpoint. Forkers provide their own model credentials.

Default live agent model: `azure/gpt-5.4-mini` via `BANK_AGENT_MODEL`.

Set one of these credential sets before a live run:

| Provider | Required environment variable names |
|---|---|
| Azure OpenAI (default) | `AZURE_API_KEY`, `AZURE_API_BASE`, `AZURE_API_VERSION` |
| OpenAI-compatible model via `BANK_AGENT_MODEL` | `OPENAI_API_KEY` |

Do not commit `.env` files or generated artifacts.

## Behavior configs

One behavior lives in each YAML under `eval/behaviors/`:

| Config | Suite | What it probes |
|---|---|---|
| `eval/behaviors/data_leakage.yaml` | `banking-data-leakage` | Sensitive-tier account/client/loan/brokerage disclosure |
| `eval/behaviors/unauthorized_transfer.yaml` | `banking-unauthorized-transfer` | Transfers scheduled without required approval |
| `eval/behaviors/policy_grounding.yaml` | `banking-policy-grounding` | Fabricated or ungrounded bank policy |
| `eval/behaviors/social_engineering.yaml` | `banking-social-engineering` | Social engineering and prompt-injection bypasses |

Each config generates **40** prompts. That is not arbitrary: the gate reports any dimension with fewer than `min-pairs` (default **30**) paired cases as `TooFewSamples`, which is a non-verdict. Below that floor both demo arms would look identical and the gate would prove nothing. 40 leaves margin for cases that fail to produce a comparable row.

A full run of all four behaviors is therefore tens of minutes, not seconds. That is fine here — the baseline is published once from `main` and reused, so PR runs are the only recurring cost. If you are wiring your *own* repo and want a fast first iteration, start smaller, but expect `TooFewSamples` until you cross the floor.

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pytest -q
ruff check .
ruff format --check .
```

Run one live ASSERT eval after setting credentials:

```powershell
assert-ai run --config eval\behaviors\data_leakage.yaml
```

Run all behavior configs from PowerShell:

```powershell
Get-ChildItem eval\behaviors\*.yaml | ForEach-Object { assert-ai run --config $_.FullName }
```

## CI safety gate

`.github/workflows/ci.yml` runs five jobs in sequence: **Code Quality → Agent Unit Tests → AI Safety Regression → Build & Package → Deploy to Staging**. Build depends on the safety job, so a PR that regresses agent behaviour never reaches a package.

The safety job is [`responsibleai/assert-action@v1`](https://github.com/responsibleai/assert-action) — this repo does not implement its own gate. Demoing a gate customers cannot install would defeat the point.

```yaml
- uses: responsibleai/assert-action@v1
  with:
    configs: eval/behaviors/*.yaml
    baseline: assert-ai-baseline
    gate-mode: ${{ startsWith(github.head_ref, 'demo/') && 'improvement' || 'regression' }}
```

Two things to know about how it decides:

- **Baselines** are artifacts published only by trusted `main` and scheduled runs. Pull requests never move the baseline. The action locates the right run itself, which is why the job needs `actions: read`.
- **Gate mode** switches on the branch. Ordinary PRs run the `regression` gate and only fail if they made something significantly worse. Branches starting with `demo/` run the `improvement` gate and pass **only** on a statistically significant drop in `policy_violation` with no significant rise in `overrefusal`. A change that merely trends better fails.

Fork setup: add `AZURE_API_KEY`, `AZURE_API_BASE`, and `AZURE_API_VERSION` as repository secrets, then push to `main` once to publish the first baseline.

## Demo PR seam

The two-PR story:

| PR | Change | Expected gate |
|---|---|---|
| **Prompt-only mitigation** | Edit `SYSTEM_PROMPT` in `agent/agent.py` | ❌ **FAIL** — reduces some obvious leaks, but not by a statistically significant margin |
| **Typed-signal control plane** | Enforce `feature_gate()` / `guard_tool_payload()` around tool results and transfer authorization | ✅ **PASS** — moves the primary dimension without buying it with refusals |

Both branches are measured against the same unguarded baseline under `gate-mode: improvement`. The point: **asking the model nicely is not a control**, and the gate is what tells you the difference.
