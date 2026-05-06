"""
Gary — independent audit protocol for AI agent plans.

Before execution: Gary checks the plan against the full LLM failure mode taxonomy.
Gary is never the same LLM as the agent being audited.

    from gary import Gary, Verdict, GaryVerdict
"""

from gary.protocol import Gary, LLMBackend
from gary.verdict import GaryVerdict, Verdict

__all__ = ["Gary", "GaryVerdict", "Verdict", "LLMBackend"]

__version__ = "0.1.0"
