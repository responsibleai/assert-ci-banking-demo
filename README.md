# assert-ci-banking-demo

A customer-safe sandbox for running **[ASSERT](https://github.com/responsibleai/ASSERT)** against a live, intentionally imperfect retail-bank manager agent.

The agent is now a real **LangGraph** tool-using agent. It can look up accounts, clients, loans, brokerage records, policy snippets, and schedule transfers. Tool results carry a typed `risk_tier` signal (`standard`, `vip`, `high_net_worth`, `restricted`). The default agent is deliberately unguarded so ASSERT has real failures to find: it may disclose sensitive-tier records, schedule transfers without required approval, or invent unsupported policy.

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

Each config caps generated prompts at **8**. That keeps a BYO-key bugbash iteration to minutes rather than tens of minutes while still giving the gate multiple cases per behavior.

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

## Current CI note

The existing `.github/workflows/ci.yml` and `scripts\*.py` are legacy demo plumbing and are intentionally unchanged in this workstream. A later step will replace them with the published `responsibleai/assert-action@v1` workflow. Until then, treat the behavior YAMLs above as the live ASSERT surface for this repo.

## Demo PR seam

The two-PR story remains achievable:

1. **Prompt-only mitigation:** edit `SYSTEM_PROMPT` in `agent\agent.py`. This should reduce some obvious leaks but is expected not to clear the improvement gate reliably.
2. **Typed-signal control plane:** enforce `feature_gate()` / `guard_tool_payload()` around tool results and transfer authorization facts before details or actions reach the model. This is the structural seam intended to pass.
