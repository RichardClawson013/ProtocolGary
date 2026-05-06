"""
Protocol Gary — independent audit protocol for AI agents.

Before execution: Gary reviews the plan.
After execution: Gary verifies the outcome.
Gary is never the same LLM as the agent being audited.

  from gary import GaryProtocol, Judgment, GaryVerdict
"""

from gary.protocol import GaryProtocol, GaryVerdict, Judgment, LLMBackend

__all__ = ["GaryProtocol", "Judgment", "GaryVerdict", "LLMBackend"]

__version__ = "0.1.0"
