"""
The failure mode taxonomy Gary checks every plan against.

Source: production LLM failure analysis across hallucination, tool use,
reasoning, security, cost, and loop failures.
"""

TAXONOMY: dict[str, str] = {
    "HAL-01": "Fabricated facts — plan relies on unverifiable or potentially false information",
    "HAL-02": "Fabricated capabilities — plan claims actions the agent cannot actually perform",
    "HAL-03": "Imaginary tools — plan references tools or APIs that may not exist",
    "TOOL-01": "Parameter hallucination — wrong or invented arguments for a tool call",
    "TOOL-02": "Action-promise gap — agent may claim success without actual execution",
    "TOOL-03": "Infinite loop risk — no clear termination criteria, could repeat endlessly",
    "TOOL-04": "Tool output misinterpretation — an error response could be treated as success",
    "LOG-01": "Logical inconsistency — contradictory statements or invalid reasoning chain",
    "LOG-02": "Numerical error — calculations performed without external verification",
    "LOG-04": "Step skipping — critical reasoning or verification steps omitted",
    "SEC-01": "Prompt injection risk — plan processes untrusted external input",
    "SEC-02": "Indirect injection — external data source could override agent instructions",
    "MEM-01": "Context loss — plan depends on information that may have been forgotten",
    "ALIGN-01": "Goal misalignment — plan may be optimizing for the wrong objective",
    "ALIGN-02": "Irreversibility — action cannot be undone if something goes wrong",
    "COST-01": "Runaway spending — plan could trigger excessive API or token usage",
    "LOOP-01": "Non-termination — no explicit stop condition or exit criteria defined",
    "DRIFT-01": "Instruction drift — plan may deviate from the original task requirements",
    "SPEC-01": "Ambiguous specification — plan is too vague to verify correctness",
    "VERIFY-01": "Missing verification — plan claims completion without checking the outcome",
}
