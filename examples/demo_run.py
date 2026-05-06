"""
examples/demo_run.py — Scripted demo for Protocol Gary.

Shows the full audit flow in action:
  - Agent builds a plan
  - Gary reviews it BEFORE execution (plan review)
  - Agent executes
  - Gary verifies the outcome AFTER execution (outcome review)
  - Shows what happens when Gary blocks a plan
  - Shows what happens when Gary detects a deviation

Run it:
    pip install -e .
    python examples/demo_run.py
"""

import time
import json

from gary import GaryProtocol, Judgment

CYAN   = "\033[36m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

SEP = BOLD + "─" * 60 + RESET


def pause(n: float = 0.15) -> None:
    time.sleep(n)


def show(text: str, color: str = "", indent: int = 0) -> None:
    prefix = "  " * indent
    print(color + prefix + text + RESET, flush=True)
    pause()


def section(title: str) -> None:
    print()
    print(SEP)
    show(title, BOLD)
    print(SEP)
    pause(0.1)


def show_plan(plan: dict) -> None:
    show("plan:", DIM)
    for line in json.dumps(plan, indent=2).splitlines():
        show(line, CYAN, indent=1)
    pause(0.05)


def show_verdict(verdict, label: str = "") -> None:
    if label:
        show(label, DIM)
    judgment_color = {
        Judgment.approved: GREEN,
        Judgment.blocked: RED,
        Judgment.escalate: YELLOW,
    }.get(verdict.judgment, RESET)

    show(f"judgment : {verdict.judgment.value.upper()}", judgment_color + BOLD)
    show(f"reason   : {verdict.reason}", DIM)
    show(f"risk     : {verdict.risk}", DIM)
    show(f"phase    : {verdict.phase}", DIM)
    show(f"hash     : {verdict.plan_hash}", DIM)
    pause(0.05)


# ── Stubs that simulate different LLM responses ──────────────────────────────

def llm_approves(prompt: str) -> str:
    return '{"judgment": "approved", "reason": "Plan is specific, reversible, and low-risk.", "risk": "low"}'


def llm_blocks(prompt: str) -> str:
    return '{"judgment": "blocked", "reason": "Irreversible payment of €9,500 with no confirmation step. Stop.", "risk": "high"}'


def llm_escalate_deviation(prompt: str) -> str:
    return '{"judgment": "escalate", "reason": "Outcome email address differs from plan. Action may have reached unintended recipient.", "risk": "medium"}'


def main() -> None:
    print()
    print(BOLD + "=" * 60 + RESET)
    print(BOLD + "Protocol Gary — Independent Audit Demo" + RESET)
    print(BOLD + "=" * 60 + RESET)
    show("The AI that checks the other AI's work.", DIM)
    pause(0.2)

    # ── Scenario 1: Approved plan, matching outcome ───────────────────────
    section("Scenario 1 — Plan approved, outcome matches")

    show("An agent wants to send a confirmation email.", DIM)
    show("Gary reviews the plan before execution.", DIM)
    print()
    pause(0.1)

    gary = GaryProtocol(llm_approves)

    plan = {
        "tool": "send_email",
        "to": "client@acmecorp.com",
        "subject": "Invoice #1042",
    }
    show_plan(plan)

    show("Gary reviewing plan...", DIM)
    pause(0.2)

    before = gary.review_plan(plan, context={"client": "Acme Corp"})
    show_verdict(before, "Gary's verdict — BEFORE execution:")
    print()

    show("Agent executes. Outcome received.", DIM)
    pause(0.1)

    outcome = {"status": "queued", "to": "client@acmecorp.com"}
    show("outcome:", DIM)
    for line in json.dumps(outcome, indent=2).splitlines():
        show(line, CYAN, indent=1)
    pause(0.05)

    show("Gary verifying outcome...", DIM)
    pause(0.2)

    after = gary.review_outcome(plan, outcome)
    show_verdict(after, "Gary's verdict — AFTER execution:")

    assert before.plan_hash == after.plan_hash
    show(f"Plan hash matches before/after: {before.plan_hash}  ✓", GREEN)

    # ── Scenario 2: Gary blocks a plan ───────────────────────────────────
    section("Scenario 2 — Gary blocks a risky plan")

    show("An agent wants to process a large payment without confirmation.", DIM)
    show("Gary reviews the plan and blocks it.", DIM)
    print()
    pause(0.1)

    gary_strict = GaryProtocol(llm_blocks)

    risky_plan = {
        "tool": "process_payment",
        "amount": 9500,
        "currency": "EUR",
        "to": "vendor@offshore.example",
    }
    show_plan(risky_plan)

    show("Gary reviewing plan...", DIM)
    pause(0.2)

    blocked = gary_strict.review_plan(risky_plan)
    show_verdict(blocked, "Gary's verdict:")
    print()
    show("Action never executed. Gary stopped it before it happened.", RED)

    # ── Scenario 3: Outcome deviates from plan ────────────────────────────
    section("Scenario 3 — Outcome deviates from plan")

    show("Plan was approved. But the outcome doesn't match what was planned.", DIM)
    show("Gary detects the deviation and escalates.", DIM)
    print()
    pause(0.1)

    gary_watchful = GaryProtocol(llm_escalate_deviation)

    approved_plan = {
        "tool": "send_email",
        "to": "client@acmecorp.com",
        "subject": "Contract renewal",
    }
    actual_outcome = {
        "status": "sent",
        "to": "ceo@acmecorp.com",  # ← different recipient!
        "subject": "Contract renewal",
    }

    show("approved plan:", DIM)
    for line in json.dumps(approved_plan, indent=2).splitlines():
        show(line, CYAN, indent=1)
    pause(0.05)

    show("actual outcome:", DIM)
    for line in json.dumps(actual_outcome, indent=2).splitlines():
        show(line, YELLOW, indent=1)
    pause(0.05)

    show("Gary verifying outcome...", DIM)
    pause(0.2)

    deviated = gary_watchful.review_outcome(approved_plan, actual_outcome)
    show_verdict(deviated, "Gary's verdict:")
    print()
    show("Escalated to operator. Human decides what happens next.", YELLOW)

    # ── Scenario 4: LLM returns garbage — Gary escalates ──────────────────
    section("Scenario 4 — LLM returns unparseable response")

    show("What happens if Gary's own LLM returns something unreadable?", DIM)
    show("Gary escalates automatically. It never fails silently.", DIM)
    print()
    pause(0.1)

    gary_broken = GaryProtocol(lambda _: "I think the plan is probably fine but I'm not sure, let me think...")

    broken = gary_broken.review_plan({"tool": "something"})
    show_verdict(broken, "Gary's verdict:")
    show("Parse failure → automatic escalate. Human sees exactly what happened.", YELLOW)

    # ── Summary ───────────────────────────────────────────────────────────
    print()
    print(BOLD + "=" * 60 + RESET)
    print(BOLD + "The rule" + RESET)
    print(BOLD + "=" * 60 + RESET)
    print()
    show("Gary's LLM must be different from the agent's LLM.", BOLD)
    print()
    show("Same model = mirror, not review.", DIM)
    show("Different model = real independent check.", GREEN)
    print()
    print(BOLD + "=" * 60 + RESET)
    print()


if __name__ == "__main__":
    main()
