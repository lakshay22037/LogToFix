from typing import List, Optional

SYSTEM_PROMPT = (
    "You are a code-fix assistant inside an internal production monitoring "
    "tool. You are shown a production error, the exact code that raised it, "
    "the commit that introduced it, and — when available — similar bugs "
    "that were fixed before in other projects. Propose a fix as a unified "
    "diff against the shown code context, explain the root cause in plain "
    "language, and give a confidence score between 0 and 1 for how likely "
    "your fix correctly resolves the error — be honest and conservative; a "
    "low confidence score is expected and useful when the fix is uncertain. "
    "Treat the similar past fixes as reference context, not a template to "
    "copy blindly — they may not apply directly to this codebase. A human "
    "always reviews your suggestion before it is applied — never claim the "
    "fix has already been applied."
)


def _format_retrieved_examples(retrieved_examples: List[dict]) -> str:
    if not retrieved_examples:
        return "No similar past fixes were found."

    blocks = []
    for i, example in enumerate(retrieved_examples, start=1):
        blocks.append(
            f"Example {i} (source: {example['source']}, distance: {example['distance']:.3f}):\n"
            f"Bug: {example['error_description'][:500]}\n"
            f"Fix:\n{example['fix_diff'][:1000]}"
        )
    return "\n\n".join(blocks)


def build_user_prompt(
    message: str,
    stack_trace: str,
    correlation: dict,
    code_context: str,
    retrieved_examples: Optional[List[dict]] = None,
) -> str:
    return (
        f"Error message: {message}\n\n"
        f"Stack trace:\n{stack_trace}\n\n"
        f"Introduced in commit {correlation['commit'][:8]} by {correlation['author']}: "
        f"\"{correlation['summary']}\"\n\n"
        f"Code context ({correlation['file']}, around line {correlation['line']}):\n"
        f"{code_context}\n\n"
        f"Similar past fixes from other projects:\n"
        f"{_format_retrieved_examples(retrieved_examples or [])}"
    )
