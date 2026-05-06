from __future__ import annotations

"""
Protocol Gary — independent external audit protocol for AI agents.

Core principle:
  The LLM that makes a plan does NOT verify that plan itself.
  Gary is a separate, independent LLM that:

  1. Reviews the plan BEFORE execution  → review_plan()
  2. Verifies the outcome AFTER execution → review_outcome()

Gary is VISIBLE to the rest of the system.
Gary is NEVER the same model as the agent being audited.
Gary NEVER fails silently — unparseable responses automatically escalate.

LLM backend interface:
  A callable that receives a string prompt and returns a string response.
  The caller provides the actual model (or a stub in tests).

Usage::

    def my_llm(prompt: str) -> str:
        return openai.complete(prompt)  # any LLM — different from your agent's

    gary = GaryProtocol(my_llm)

    # Step 1: BEFORE execution
    verdict = gary.review_plan(plan, context={"client": "Acme Corp"})
    if verdict.judgment != Judgment.approved:
        raise BlockedByGary(verdict.reason)

    # Step 2: execute the action
    outcome = execute(plan)

    # Step 3: AFTER execution
    post_verdict = gary.review_outcome(plan, outcome)
    if post_verdict.judgment == Judgment.escalate:
        notify_operator(post_verdict)
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Callable

from pydantic import BaseModel, Field


LLMBackend = Callable[[str], str]


class Judgment(str, Enum):
    approved = "approved"
    blocked = "blocked"
    escalate = "escalate"


class GaryVerdict(BaseModel):
    verdict_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    judgment: Judgment
    reason: str
    risk: str = "unknown"        # low / medium / high
    plan_hash: str
    phase: str                    # "before" or "after"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_response: str = ""        # raw LLM output — always preserved for audit


def _hash_plan(plan: dict) -> str:
    raw = json.dumps(plan, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _build_plan_prompt(plan: dict, context: dict) -> str:
    return (
        "You are an independent auditor (Protocol Gary).\n"
        "Review the following plan BEFORE it is executed.\n"
        "You are NOT the agent that created this plan. You are the reviewer.\n\n"
        f"PLAN:\n{json.dumps(plan, indent=2)}\n\n"
        f"CONTEXT:\n{json.dumps(context, indent=2)}\n\n"
        "Respond ONLY with valid JSON in this exact format:\n"
        '{"judgment": "approved" | "blocked" | "escalate", '
        '"reason": "...", "risk": "low" | "medium" | "high"}\n'
        "No text outside the JSON."
    )


def _build_outcome_prompt(plan: dict, outcome: dict) -> str:
    return (
        "You are an independent auditor (Protocol Gary).\n"
        "Verify whether the outcome matches the approved plan.\n"
        "You are NOT the agent that executed this. You are the reviewer.\n\n"
        f"PLAN:\n{json.dumps(plan, indent=2)}\n\n"
        f"OUTCOME:\n{json.dumps(outcome, indent=2)}\n\n"
        "Respond ONLY with valid JSON in this exact format:\n"
        '{"judgment": "approved" | "blocked" | "escalate", '
        '"reason": "...", "risk": "low" | "medium" | "high"}\n'
        "No text outside the JSON."
    )


def _parse_verdict(response: str, plan_hash: str, phase: str) -> GaryVerdict:
    """
    Parse LLM response into a GaryVerdict.
    On parse failure: always escalate — Gary never fails silently.
    """
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("no JSON object found in response")
        data = json.loads(response[start:end])
        try:
            judgment = Judgment(data.get("judgment", "escalate"))
        except ValueError:
            judgment = Judgment.escalate
        return GaryVerdict(
            judgment=judgment,
            reason=data.get("reason", "no reason provided"),
            risk=data.get("risk", "unknown"),
            plan_hash=plan_hash,
            phase=phase,
            raw_response=response,
        )
    except Exception as exc:
        return GaryVerdict(
            judgment=Judgment.escalate,
            reason=f"Gary could not parse the LLM response: {exc}",
            plan_hash=plan_hash,
            phase=phase,
            raw_response=response,
        )


class GaryProtocol:
    """
    Protocol Gary — independent external audit protocol.

    Accepts an LLMBackend: Callable[[str], str]
    In production: provide a different model than your agent uses.
    In tests: provide a stub that returns fixed JSON.
    """

    def __init__(self, llm_backend: LLMBackend) -> None:
        self._llm = llm_backend

    def review_plan(
        self, plan: dict, context: dict | None = None
    ) -> GaryVerdict:
        """
        BEFORE execution: approve the plan, block it, or escalate to operator.
        Call this before the agent executes any action.
        """
        plan_hash = _hash_plan(plan)
        response = self._llm(_build_plan_prompt(plan, context or {}))
        return _parse_verdict(response, plan_hash, phase="before")

    def review_outcome(
        self, plan: dict, outcome: dict
    ) -> GaryVerdict:
        """
        AFTER execution: verify the outcome matches the approved plan.
        Escalates if the outcome deviates from what was planned.
        """
        plan_hash = _hash_plan(plan)
        response = self._llm(_build_outcome_prompt(plan, outcome))
        return _parse_verdict(response, plan_hash, phase="after")
