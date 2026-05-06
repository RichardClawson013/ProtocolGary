"""
Protocol Gary test suite.

Core principle every test guards:
  The LLM that makes a plan does NOT verify that plan itself.
  Gary is an independent LLM. Before execution. After execution.
  Gary never fails silently — parse errors automatically escalate.
"""

import pytest

from gary import GaryProtocol, GaryVerdict, Judgment


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


def _stub_approved(prompt: str) -> str:
    return '{"judgment": "approved", "reason": "Plan is safe and clear", "risk": "low"}'


def _stub_blocked(prompt: str) -> str:
    return '{"judgment": "blocked", "reason": "Irreversible payment without confirmation", "risk": "high"}'


def _stub_escalate(prompt: str) -> str:
    return '{"judgment": "escalate", "reason": "Deviation detected", "risk": "medium"}'


def _stub_broken(prompt: str) -> str:
    return "Here is my response: I think the plan is fine but I won't write JSON."


# ---------------------------------------------------------------------------
# Step 1: review plan BEFORE execution
# ---------------------------------------------------------------------------


def test_review_plan_approved():
    gary = GaryProtocol(_stub_approved)
    plan = {"tool": "send_email", "to": "client@company.com"}
    verdict = gary.review_plan(plan)

    assert verdict.judgment == Judgment.approved
    assert verdict.phase == "before"
    assert verdict.plan_hash


def test_review_plan_blocked():
    gary = GaryProtocol(_stub_blocked)
    plan = {"tool": "process_payment", "amount": 9500}
    verdict = gary.review_plan(plan)

    assert verdict.judgment == Judgment.blocked
    assert verdict.risk == "high"


def test_review_plan_with_context():
    gary = GaryProtocol(_stub_approved)
    plan = {"tool": "send_email"}
    verdict = gary.review_plan(plan, context={"client": "Acme Corp", "sector": "retail"})

    assert verdict.judgment == Judgment.approved


# ---------------------------------------------------------------------------
# Step 2: review outcome AFTER execution
# ---------------------------------------------------------------------------


def test_review_outcome_approved():
    gary = GaryProtocol(_stub_approved)
    plan = {"tool": "send_email", "to": "client@company.com"}
    outcome = {"status": "queued", "to": "client@company.com"}

    verdict = gary.review_outcome(plan, outcome)
    assert verdict.judgment == Judgment.approved
    assert verdict.phase == "after"


def test_review_outcome_escalate_on_deviation():
    gary = GaryProtocol(_stub_escalate)
    plan = {"tool": "send_email", "to": "client@company.com"}
    outcome = {"status": "sent", "to": "WRONG@company.com"}  # deviation!

    verdict = gary.review_outcome(plan, outcome)
    assert verdict.judgment == Judgment.escalate


# ---------------------------------------------------------------------------
# Before/after flow — full cycle
# ---------------------------------------------------------------------------


def test_before_after_same_plan_hash():
    """Same plan_hash in before/after verdict proves they refer to the same plan."""
    gary = GaryProtocol(_stub_approved)
    plan = {"tool": "send_email", "to": "client@company.com", "subject": "Update"}

    before = gary.review_plan(plan)
    after = gary.review_outcome(plan, {"status": "queued"})

    assert before.plan_hash == after.plan_hash
    assert before.phase == "before"
    assert after.phase == "after"


# ---------------------------------------------------------------------------
# Robustness — Gary never fails silently
# ---------------------------------------------------------------------------


def test_parse_failure_escalates():
    """If the LLM returns no valid JSON, Gary escalates automatically."""
    gary = GaryProtocol(_stub_broken)
    verdict = gary.review_plan({"tool": "something"})

    assert verdict.judgment == Judgment.escalate
    assert "parse" in verdict.reason.lower()


def test_empty_response_escalates():
    gary = GaryProtocol(lambda _: "")
    verdict = gary.review_plan({"tool": "something"})
    assert verdict.judgment == Judgment.escalate


def test_raw_response_always_preserved():
    """Raw LLM output is always preserved — for audit, never discarded."""
    gary = GaryProtocol(_stub_approved)
    verdict = gary.review_plan({"tool": "x"})
    assert "approved" in verdict.raw_response


def test_unknown_judgment_value_escalates():
    """Unknown judgment value falls back to escalate."""
    def stub(_): return '{"judgment": "maybe", "reason": "unsure", "risk": "low"}'
    gary = GaryProtocol(stub)
    verdict = gary.review_plan({"tool": "x"})
    assert verdict.judgment == Judgment.escalate


# ---------------------------------------------------------------------------
# Independence — architectural principle
# ---------------------------------------------------------------------------


def test_gary_uses_its_own_llm_not_the_agents():
    """
    Gary and the agent each call their own LLM.
    They never share a backend — that is the core principle.
    """
    agent_calls = []
    gary_calls = []

    def agent_llm(prompt: str) -> str:
        agent_calls.append(prompt)
        return "plan: send confirmation email to client"

    def gary_llm(prompt: str) -> str:
        gary_calls.append(prompt)
        return '{"judgment": "approved", "reason": "ok", "risk": "low"}'

    gary = GaryProtocol(gary_llm)
    _ = agent_llm("draft an email to the client")
    verdict = gary.review_plan({"tool": "send_email"})

    assert len(agent_calls) == 1
    assert len(gary_calls) == 1
    assert agent_calls[0] != gary_calls[0]
    assert "Protocol Gary" in gary_calls[0]
    assert verdict.judgment == Judgment.approved


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_plan_hash_is_deterministic():
    gary = GaryProtocol(_stub_approved)
    plan = {"tool": "send_email", "to": "a@b.com"}
    v1 = gary.review_plan(plan)
    v2 = gary.review_plan(plan)
    assert v1.plan_hash == v2.plan_hash


def test_different_plans_different_hash():
    gary = GaryProtocol(_stub_approved)
    v1 = gary.review_plan({"tool": "send_email"})
    v2 = gary.review_plan({"tool": "process_payment"})
    assert v1.plan_hash != v2.plan_hash
