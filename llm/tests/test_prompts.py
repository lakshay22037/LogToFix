from llm_core.prompts import build_user_prompt

CORRELATION = {
    "commit": "abc12345def",
    "author": "Jane Dev",
    "summary": "Seed bug: something",
    "file": "app.py",
    "line": 42,
}


def test_build_user_prompt_includes_all_sections():
    prompt = build_user_prompt(
        message="boom",
        stack_trace="Traceback...\nValueError: boom",
        correlation=CORRELATION,
        code_context="42: raise ValueError('boom')",
    )

    assert "boom" in prompt
    assert "abc12345" in prompt  # truncated commit hash
    assert "Jane Dev" in prompt
    assert "app.py" in prompt
    assert "raise ValueError" in prompt
    assert "No similar past fixes were found." in prompt


def test_build_user_prompt_includes_retrieved_examples():
    retrieved = [
        {"source": "swebench-lite:foo-1", "distance": 0.123, "error_description": "a bug", "fix_diff": "- old\n+ new"},
    ]
    prompt = build_user_prompt(
        message="boom",
        stack_trace="trace",
        correlation=CORRELATION,
        code_context="context",
        retrieved_examples=retrieved,
    )

    assert "swebench-lite:foo-1" in prompt
    assert "0.123" in prompt
    assert "a bug" in prompt
    assert "No similar past fixes were found." not in prompt
