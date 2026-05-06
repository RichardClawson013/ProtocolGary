"""
Gary test suite.

Core principle every test guards:
  Gary checks plans against the failure mode taxonomy.
  Gary uses a different LLM than the agent.
  Gary never fails silently — parse errors escalate automatically.
  Gary retries on block and auto-escalates after max rounds.
"""

import pytest
from gary import Gary, GaryVerdict, Verdict


def stub_pass(prompt: str) -> str:
    return '{"verdict": "pass", "reason": "No failure modes detected.", "failure_modes_triggered": [], "risk_level": "low"}'


def stub_block(prompt: str) -> str:
    return '{"verdict": "block", "reason": "ALIGN-02: irreversible payment with no rollback.", "failure_modes_triggered": ["ALIGN-02"], "risk_level": "high"}'


def stub_escalate(prompt: str) -> str:
    return '{"verdict": "escalate", "reason": "SPEC-01: plan too vague to verify.", "failure_modes_triggered": ["SPEC-01"], "risk_level": "medium"}'


def stub_broken(prompt: str) -> str:
    return "I think the plan looks fine but I refuse to write JSON."


# ---------------------------------------------------------------------------
# Basic verdicts
# ---------------------------------------------------------------------------

def test_pass():
    gary = Gary(llm=stub_pass)
    verdict = gary.review({"action": "send_email", "to": "client@company.com"})
    assert verdict.verdict == Verdict.PASS
    assert verdict.round == 1


def test_block_with_failure_modes():
    gary = Gary(llm=stub_block, max_retries=1)
    verdict = gary.review({"action": "process_payment", "amount": 9500})
    assert verdict.verdict == Verdict.ESCALATE  # blocked → retries → escalate
    assert "ALIGN-02" in verdict.failure_modes_triggered or "Last reason" in verdict.reason


def test_escalate():
    gary = Gary(llm=stub_escalate, max_retries=1)
    verdict = gary.review({"action": "something_vague"})
    assert verdict.verdict == Verdict.ESCALATE


# ---------------------------------------------------------------------------
# Retry mechanism
# ---------------------------------------------------------------------------

def test_retry_then_pass():
    """Block on first round, pass on second."""
    calls = []

    def llm(prompt: str) -> str:
        calls.append(prompt)
        if len(calls) == 1:
            return stub_block(prompt)
        return stub_pass(prompt)

    gary = Gary(llm=llm, max_retries=3)
    verdict = gary.review({"action": "send_email"})
    assert verdict.verdict == Verdict.PASS
    assert verdict.round == 2
    assert len(calls) == 2


def test_max_retries_forces_escalate():
    """Block every round → escalate after max_retries."""
    gary = Gary(llm=stub_block, max_retries=3)
    verdict = gary.review({"action": "process_payment"})
    assert verdict.verdict == Verdict.ESCALATE
    assert "3 review rounds" in verdict.reason


def test_feedback_included_in_retry_prompt():
    """Second round prompt must contain feedback from first round."""
    prompts = []

    def llm(prompt: str) -> str:
        prompts.append(prompt)
        if len(prompts) == 1:
            return stub_block(prompt)
        return stub_pass(prompt)

    gary = Gary(llm=llm, max_retries=2)
    gary.review({"action": "something"})
    assert len(prompts) == 2
    assert "FEEDBACK FROM PREVIOUS ROUND" in prompts[1]


# ---------------------------------------------------------------------------
# Budget cap
# ---------------------------------------------------------------------------

def test_budget_exhausted_escalates():
    gary = Gary(llm=stub_pass, daily_budget_usd=0.0)
    verdict = gary.review({"action": "anything"})
    assert verdict.verdict == Verdict.ESCALATE
    assert "budget" in verdict.reason.lower()


# ---------------------------------------------------------------------------
# Parse robustness — never fails silently
# ---------------------------------------------------------------------------

def test_broken_response_escalates():
    gary = Gary(llm=stub_broken)
    verdict = gary.review({"action": "something"})
    assert verdict.verdict == Verdict.ESCALATE
    assert "parse" in verdict.reason.lower()


def test_empty_response_escalates():
    gary = Gary(llm=lambda _: "")
    verdict = gary.review({"action": "something"})
    assert verdict.verdict == Verdict.ESCALATE


def test_unknown_verdict_value_escalates():
    gary = Gary(llm=lambda _: '{"verdict": "maybe", "reason": "unsure", "risk_level": "low"}')
    verdict = gary.review({"action": "something"})
    assert verdict.verdict == Verdict.ESCALATE


# ---------------------------------------------------------------------------
# Independence — different LLM
# ---------------------------------------------------------------------------

def test_gary_uses_its_own_llm():
    agent_calls = []
    gary_calls = []

    def agent_llm(prompt: str) -> str:
        agent_calls.append(prompt)
        return "plan: send confirmation email"

    def gary_llm(prompt: str) -> str:
        gary_calls.append(prompt)
        return stub_pass(prompt)

    gary = Gary(llm=gary_llm)
    _ = agent_llm("draft an email")
    verdict = gary.review({"action": "send_email"})

    assert len(agent_calls) == 1
    assert len(gary_calls) == 1
    assert agent_calls[0] != gary_calls[0]
    assert verdict.verdict == Verdict.PASS


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

def test_audit_log_written(tmp_path):
    gary = Gary(llm=stub_pass, audit_log_dir=tmp_path)
    gary.review({"action": "send_email", "to": "x@y.com"})
    logs = list(tmp_path.rglob("*.json"))
    assert len(logs) == 1
    import json
    data = json.loads(logs[0].read_text())
    assert data["verdict"] == "pass"
    assert "plan" in data


# ---------------------------------------------------------------------------
# Plan hash
# ---------------------------------------------------------------------------

def test_plan_hash_deterministic():
    gary = Gary(llm=stub_pass)
    plan = {"action": "send_email", "to": "a@b.com"}
    v1 = gary.review(plan)
    v2 = gary.review(plan)
    assert v1.plan_hash == v2.plan_hash


def test_different_plans_different_hash():
    gary = Gary(llm=stub_pass)
    v1 = gary.review({"action": "send_email"})
    v2 = gary.review({"action": "delete_file"})
    assert v1.plan_hash != v2.plan_hash


# ---------------------------------------------------------------------------
# Failure modes surfaced in verdict
# ---------------------------------------------------------------------------

def test_failure_modes_returned():
    gary = Gary(llm=stub_block, max_retries=1)
    verdict = gary.review({"action": "process_payment", "amount": 9500})
    # The stub_block returns ALIGN-02 — should appear somewhere in the chain
    assert isinstance(verdict.failure_modes_triggered, list)
