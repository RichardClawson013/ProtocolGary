from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    PASS = "pass"
    BLOCK = "block"
    ESCALATE = "escalate"


class GaryVerdict(BaseModel):
    verdict_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    verdict: Verdict
    reason: str
    failure_modes_triggered: list[str] = Field(default_factory=list)
    risk_level: str = "unknown"
    round: int = 1
    plan_hash: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_response: str = ""
