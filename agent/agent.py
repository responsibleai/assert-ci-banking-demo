"""Minimal bank-manager agent with a typed-feature safety gate.

Sanitized, self-contained stand-in for the ASSERT `bank_manager_agent_control`
example. The gate decides on the *typed risk signal the tool emits*
(``risk_tier``) rather than a regex over stringified ids — the same principle the
full demo evaluates. No network or model calls, so unit tests run offline.
"""

from __future__ import annotations

from dataclasses import dataclass

SENSITIVE_TIERS = frozenset({"vip", "high_net_worth", "restricted"})


@dataclass(frozen=True)
class Decision:
    allow: bool
    reason: str
    message: str


def feature_gate(risk_tier: str, *, authorized: bool = False) -> Decision:
    """Gate a sensitive read on the typed ``risk_tier`` the tool returned.

    Blocks any sensitive-tier record the caller has not been authorized for,
    regardless of the entity's id prefix (account, loan, brokerage, client).
    """
    tier = (risk_tier or "standard").lower()
    if tier in SENSITIVE_TIERS and not authorized:
        return Decision(
            allow=False,
            reason="sensitive_read_gate",
            message=(
                "That record is on our enhanced-protection list; its details are "
                "available only through the verified customer review portal."
            ),
        )
    return Decision(allow=True, reason="ok", message="")


def chat(message: str, *, risk_tier: str = "standard", authorized: bool = False) -> str:
    """Toy turn: a read request is gated on the record's typed risk tier."""
    decision = feature_gate(risk_tier, authorized=authorized)
    if not decision.allow:
        return decision.message
    return f"Here are the details you requested: {message}"
