SYSTEM_PROMPT = (
    "You are a code-fix assistant inside an internal production monitoring "
    "tool. You are shown a production error, the exact code that raised it, "
    "and the commit that introduced it. Propose a fix as a unified diff "
    "against the shown code context, explain the root cause in plain "
    "language, and give a confidence score between 0 and 1 for how likely "
    "your fix correctly resolves the error — be honest and conservative; a "
    "low confidence score is expected and useful when the fix is uncertain. "
    "A human always reviews your suggestion before it is applied — never "
    "claim the fix has already been applied."
)


def build_user_prompt(message: str, stack_trace: str, correlation: dict, code_context: str) -> str:
    return (
        f"Error message: {message}\n\n"
        f"Stack trace:\n{stack_trace}\n\n"
        f"Introduced in commit {correlation['commit'][:8]} by {correlation['author']}: "
        f"\"{correlation['summary']}\"\n\n"
        f"Code context ({correlation['file']}, around line {correlation['line']}):\n"
        f"{code_context}"
    )
