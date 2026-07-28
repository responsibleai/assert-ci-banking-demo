"""Unit tests for the LangGraph banking agent control seams."""

import agent.agent as banking_agent
from agent import chat, feature_gate, guard_tool_payload


def test_standard_read_is_allowed():
    decision = feature_gate("standard")
    assert decision.allow is True


def test_sensitive_read_is_blocked_by_typed_tier():
    for tier in ("vip", "high_net_worth", "restricted"):
        decision = feature_gate(tier)
        assert decision.allow is False
        assert decision.reason == "sensitive_read_gate"


def test_authorized_caller_may_read_sensitive():
    decision = feature_gate("vip", authorized=True)
    assert decision.allow is True


def test_gate_generalizes_across_record_domains():
    for payload in (
        banking_agent.lookup_account.invoke({"account_id": "ACC-2040"}),
        banking_agent.read_loan_record.invoke({"loan_id": "LN-3002"}),
        banking_agent.read_brokerage_record.invoke({"brokerage_id": "BR-7711"}),
    ):
        guarded = guard_tool_payload(payload)
        assert guarded["blocked"] is True
        assert guarded["reason"] == "sensitive_read_gate"


def test_unguarded_transfer_tool_exposes_control_gap():
    result = banking_agent.execute_transfer.invoke(
        {
            "from_account_id": "ACC-2040",
            "to_account_id": "ACC-1001",
            "amount_usd": 25000,
            "requested_by": "unverified caller",
        }
    )
    assert result["status"] == "scheduled"
    assert result["approval_required"] is True
    assert result["approval_present"] is False
    assert result["control_gap"] is True
    assert result["risk_tier"] == "vip"


def test_policy_lookup_does_not_create_grounding_for_missing_policy():
    result = banking_agent.lookup_policy.invoke({"topic": "instant crypto wire override"})
    assert result == {
        "found": False,
        "topic": "instant crypto wire override",
        "risk_tier": "standard",
        "policy_text": None,
    }


def test_chat_uses_mocked_model_path_without_network(monkeypatch):
    def fake_invoke(message: str, history=None):
        assert history is None
        return f"mocked model response for: {message}"

    monkeypatch.setattr(banking_agent, "_invoke_graph", fake_invoke)

    assert chat("show account ACC-1001") == "mocked model response for: show account ACC-1001"
