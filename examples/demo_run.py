"""
examples/demo_run.py — Scripted demo for Protocol Gary.

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


def line(text: str, color: str = "", indent: int = 0) -> None:
    prefix = "  " * indent
    print(color + prefix + text + RESET, flush=True)
    time.sleep(0.6)


def gap(n: float = 1.5) -> None:
    time.sleep(n)


def section(title: str) -> None:
    gap(2.0)
    print()
    print(SEP)
    line(title, BOLD)
    print(SEP)
    gap(1.0)


def show_dict(data: dict, color: str = DIM, indent: int = 1) -> None:
    for ln in json.dumps(data, indent=2).splitlines():
        line(ln, color, indent)


def show_verdict(verdict) -> None:
    judgment_color = {
        Judgment.approved: GREEN,
        Judgment.blocked: RED,
        Judgment.escalate: YELLOW,
    }.get(verdict.judgment, RESET)

    line(f"judgment  :  {verdict.judgment.value.upper()}", judgment_color + BOLD)
    line(f"reason    :  {verdict.reason}", DIM)
    line(f"risk      :  {verdict.risk}", DIM)
    line(f"phase     :  {verdict.phase}", DIM)
    line(f"hash      :  {verdict.plan_hash}", DIM)


def llm_approves(prompt: str) -> str:
    return '{"judgment": "approved", "reason": "Plan is specific, reversible, and low-risk.", "risk": "low"}'

def llm_blocks(prompt: str) -> str:
    return '{"judgment": "blocked", "reason": "Irreversible payment of 9500 EUR with no confirmation step.", "risk": "high"}'

def llm_deviation(prompt: str) -> str:
    return '{"judgment": "escalate", "reason": "Email address in outcome differs from approved plan.", "risk": "medium"}'


def main() -> None:
    gap(0.5)
    print()
    print(BOLD + "=" * 60 + RESET)
    print(BOLD + "Protocol Gary — Independent Audit Demo" + RESET)
    print(BOLD + "=" * 60 + RESET)
    line("The AI that checks the other AI's work.", DIM)
    gap(2.0)

    # ── Scenario 1: Approved ──────────────────────────────────────────────
    section("Scenario 1 — Plan approved, outcome matches")

    line("An agent wants to send a confirmation email.", DIM)
    line("Gary reviews the plan before anything happens.", DIM)
    gap(1.5)

    gary = GaryProtocol(llm_approves)
    plan = {
        "tool": "send_email",
        "to": "client@acmecorp.com",
        "subject": "Invoice #1042",
    }

    line("Plan:", DIM)
    show_dict(plan, CYAN)
    gap(2.0)

    line("Gary reviewing plan...", DIM)
    gap(1.5)

    before = gary.review_plan(plan, context={"client": "Acme Corp"})
    line("Gary's verdict — BEFORE execution:", DIM)
    show_verdict(before)
    gap(2.5)

    line("Plan approved. Agent executes.", DIM)
    gap(1.5)

    outcome = {"status": "queued", "to": "client@acmecorp.com"}
    line("Outcome:", DIM)
    show_dict(outcome, CYAN)
    gap(1.5)

    line("Gary verifying outcome...", DIM)
    gap(1.5)

    after = gary.review_outcome(plan, outcome)
    line("Gary's verdict — AFTER execution:", DIM)
    show_verdict(after)
    gap(1.5)

    line(f"Plan hash matches before/after: {before.plan_hash}  ✓", GREEN)

    # ── Scenario 2: Blocked ───────────────────────────────────────────────
    section("Scenario 2 — Gary blocks a risky plan")

    line("An agent wants to process a large payment without confirmation.", DIM)
    gap(1.5)

    gary2 = GaryProtocol(llm_blocks)
    risky_plan = {
        "tool": "process_payment",
        "amount": 9500,
        "currency": "EUR",
        "to": "vendor@offshore.example",
    }

    line("Plan:", DIM)
    show_dict(risky_plan, CYAN)
    gap(2.0)

    line("Gary reviewing plan...", DIM)
    gap(1.5)

    blocked = gary2.review_plan(risky_plan)
    line("Gary's verdict:", DIM)
    show_verdict(blocked)
    gap(1.5)

    line("Action never executed. Gary stopped it.", RED)

    # ── Scenario 3: Deviation ─────────────────────────────────────────────
    section("Scenario 3 — Outcome deviates from plan")

    line("Plan was approved. The outcome doesn't match.", DIM)
    gap(1.5)

    gary3 = GaryProtocol(llm_deviation)
    approved_plan = {"tool": "send_email", "to": "client@acmecorp.com"}
    actual_outcome = {"status": "sent", "to": "ceo@acmecorp.com"}

    line("Approved plan:", DIM)
    show_dict(approved_plan, CYAN)
    gap(1.5)
    line("Actual outcome:", DIM)
    show_dict(actual_outcome, YELLOW)
    gap(2.0)

    line("Gary verifying outcome...", DIM)
    gap(1.5)

    deviated = gary3.review_outcome(approved_plan, actual_outcome)
    line("Gary's verdict:", DIM)
    show_verdict(deviated)
    gap(1.5)

    line("Escalated to operator. Human decides what happens next.", YELLOW)

    # ── Summary ───────────────────────────────────────────────────────────
    gap(2.0)
    print()
    print(BOLD + "=" * 60 + RESET)
    print(BOLD + "The rule" + RESET)
    print(BOLD + "=" * 60 + RESET)
    print()
    line("Gary's LLM must be different from the agent's LLM.", BOLD)
    gap(1.0)
    line("Same model = mirror, not review.", DIM)
    line("Different model = real independent check.", GREEN)
    print()
    print(BOLD + "=" * 60 + RESET)
    gap(1.0)


if __name__ == "__main__":
    main()
