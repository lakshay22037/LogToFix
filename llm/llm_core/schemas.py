from pydantic import BaseModel, Field


class FixSuggestion(BaseModel):
    """The structured shape every LLM provider must return. Never applied
    automatically to code — always shown to a human for review (see
    ENGINEERING_STANDARDS.md and CLAUDE.md's hard rule on this)."""

    explanation: str = Field(description="Plain-language explanation of the root cause")
    diff: str = Field(description="Proposed fix as a unified diff against the shown code context")
    confidence: float = Field(ge=0, le=1, description="Confidence the fix is correct, 0-1")
