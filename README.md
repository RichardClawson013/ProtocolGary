# Protocol Gary

[![CI](https://github.com/RichardClawson013/ProtocolGary/actions/workflows/ci.yml/badge.svg)](https://github.com/RichardClawson013/ProtocolGary/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/protocol-gary)](https://pypi.org/project/protocol-gary/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/protocol-gary)](https://pypi.org/project/protocol-gary/)

> **The AI that checks the other AI's work.**

---

![Protocol Gary demo](docs/media/demo.gif)

---

## The problem

An AI agent makes a plan. Then it executes the plan. Then it tells you it succeeded.

If the plan was wrong, it was wrong from the start. If the execution deviated from the plan, you probably won't find out until something breaks. The agent that made the mistake is also the one writing the success report.

This is not a trust problem. It's a structural problem. You can't ask a system to check its own reasoning with the same reasoning it used to reason wrong. That's not review. That's repetition.

**Protocol Gary puts a second, independent AI in the loop.** Before the agent acts, Gary reviews the plan. After the agent acts, Gary checks the outcome. Gary is never the same model as the agent it's auditing.

---

## How it works

Gary sits between the plan and the action.

```
Agent builds plan
      ↓
   Gary reviews plan  ←─ independent LLM (not the agent)
      ↓
  approved? → action executes
  blocked?  → action stops, reason returned
  escalate? → goes to human operator
      ↓
   Gary reviews outcome  ←─ same independent LLM
      ↓
  approved? → done
  escalate? → outcome deviated from plan, human notified
```

Gary doesn't know your agent. Your agent doesn't know Gary. They share nothing — not the same model, not the same context, not the same call stack. That separation is the point.

---

## Install

```bash
pip install protocol-gary
```

Requires Python 3.11+. No external services. Gary accepts any LLM you give it — OpenAI, Anthropic, a local model, anything with a `str → str` interface.

---

## Demo

Copy this. Run it.

```python
from gary import GaryProtocol, Judgment

# Gary accepts any callable: prompt (str) → response (str)
# Use a different model than your agent uses.
def my_audit_llm(prompt: str) -> str:
    # Replace with your actual LLM call:
    # return openai.chat.completions.create(...).choices[0].message.content
    return '{"judgment": "approved", "reason": "Plan is specific and reversible", "risk": "low"}'

gary = GaryProtocol(my_audit_llm)

plan = {
    "tool": "send_email",
    "to": "client@company.com",
    "subject": "Invoice #1042",
}

# Step 1: before the agent acts
verdict = gary.review_plan(plan, context={"client": "Acme Corp"})
print(verdict.judgment)   # Judgment.approved
print(verdict.reason)     # "Plan is specific and reversible"
print(verdict.phase)      # "before"
print(verdict.plan_hash)  # "3f8a1c2d" ← links this verdict to the outcome check

# Step 2: execute the action (your code here)
outcome = {"status": "queued", "to": "client@company.com"}

# Step 3: after the agent acts
post_verdict = gary.review_outcome(plan, outcome)
print(post_verdict.judgment)  # Judgment.approved
print(post_verdict.phase)     # "after"

# The plan_hash matches — Gary verified before and after the same action
assert verdict.plan_hash == post_verdict.plan_hash
```

---

## What Gary returns

Every call returns a `GaryVerdict`:

```python
verdict.judgment    # Judgment.approved / Judgment.blocked / Judgment.escalate
verdict.reason      # plain-language explanation from Gary's LLM
verdict.risk        # "low" / "medium" / "high"
verdict.plan_hash   # SHA-256[:16] of the plan — same hash in before/after pair
verdict.phase       # "before" or "after"
verdict.timestamp   # when Gary reviewed
verdict.raw_response  # the exact string your LLM returned — always preserved
```

If Gary's LLM returns something unparseable, Gary automatically escalates with a clear error. It never fails silently.

---

## Using Gary with a real LLM

```python
import anthropic
from gary import GaryProtocol, Judgment

client = anthropic.Anthropic()

def claude_auditor(prompt: str) -> str:
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",   # use a different model than your agent
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text

gary = GaryProtocol(claude_auditor)

verdict = gary.review_plan({"tool": "delete_file", "path": "/data/invoices/2024.csv"})

if verdict.judgment == Judgment.blocked:
    print(f"Gary blocked this: {verdict.reason}")
elif verdict.judgment == Judgment.escalate:
    print(f"Gary needs a human: {verdict.reason}")
else:
    print("Gary approved. Proceeding.")
```

---

## The rule

One rule. No exceptions.

**Gary's LLM must be different from the agent's LLM.**

If you wire Gary to the same model, same API key, and same system prompt as your agent, you have not added a reviewer. You have added a mirror. The whole point is separation. Different model, different call, different context.

---

## Run the tests

```bash
git clone https://github.com/RichardClawson013/ProtocolGary
cd ProtocolGary
pip install -e ".[dev]"
pytest
```

13 tests. All green.

---

*Apache 2.0 — Rob de Vet*
