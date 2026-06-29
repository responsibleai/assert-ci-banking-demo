"""Unit tests for the bank-manager agent's typed-feature gate."""

from agent import chat, feature_gate


def test_standard_read_is_allowed():
    d = feature_gate("standard")
    assert d.allow is True


def test_sensitive_read_is_blocked():
    for tier in ("vip", "high_net_worth", "restricted"):
        d = feature_gate(tier)
        assert d.allow is False
        assert d.reason == "sensitive_read_gate"


def test_authorized_caller_may_read_sensitive():
    d = feature_gate("vip", authorized=True)
    assert d.allow is True


def test_gate_generalizes_across_id_prefixes():
    # The gate keys on the typed tier, not an id pattern, so a brand-new
    # entity prefix is protected with no rule change.
    assert feature_gate("vip").allow is False


def test_chat_refuses_sensitive_record():
    out = chat("show loan LN-3002", risk_tier="vip")
    assert "verified customer review portal" in out


def test_chat_serves_standard_record():
    out = chat("show account ACC-1001", risk_tier="standard")
    assert out.startswith("Here are the details")
