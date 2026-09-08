import subprocess
from pathlib import Path

import pytest

from app.correlation import (
    correlate_error_to_commit,
    extract_last_matching_frame,
    read_code_context,
)

MULTI_FRAME_TRACEBACK = """Traceback (most recent call last):
  File "/usr/lib/python3.9/threading.py", line 910, in run
    self._target(*self._args, **self._kwargs)
  File "/Users/dev/project/demo-repo/app.py", line 42, in handler
    raise ValueError("boom")
ValueError: boom"""


def test_extract_last_matching_frame_finds_deepest_app_frame():
    frame = extract_last_matching_frame(MULTI_FRAME_TRACEBACK, "demo-repo")
    assert frame == ("/Users/dev/project/demo-repo/app.py", 42)


def test_extract_last_matching_frame_returns_none_when_no_match():
    assert extract_last_matching_frame(MULTI_FRAME_TRACEBACK, "no-such-path") is None


def _init_git_repo(repo_path: Path, file_content: str) -> str:
    """Creates a one-file, one-commit git repo; returns the commit hash."""
    repo_path.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)
    (repo_path / "app.py").write_text(file_content)
    subprocess.run(["git", "add", "app.py"], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "Add app.py"], cwd=repo_path, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_path, capture_output=True, text=True, check=True
    ).stdout.strip()


def test_correlate_error_to_commit_finds_real_commit(tmp_path):
    repo_path = tmp_path / "demo-repo"
    content = "def handler():\n    raise ValueError('boom')\n"
    commit_hash = _init_git_repo(repo_path, content)

    stack_trace = (
        "Traceback (most recent call last):\n"
        f'  File "{repo_path}/app.py", line 2, in handler\n'
        "    raise ValueError('boom')\n"
        "ValueError: boom"
    )

    result = correlate_error_to_commit(stack_trace, path_filter="demo-repo")

    assert result is not None
    assert result["commit"] == commit_hash
    assert result["author"] == "Test User"
    assert result["line"] == 2


def test_correlate_error_to_commit_returns_none_without_stack_trace():
    assert correlate_error_to_commit("") is None
    assert correlate_error_to_commit(None) is None


def test_read_code_context_returns_whole_enclosing_function(tmp_path):
    content = (
        "def outer():\n"
        "    pass\n"
        "\n"
        "def target():\n"
        "    x = 1\n"
        "    y = 2\n"
        "    return x + y\n"
    )
    (tmp_path / "app.py").write_text(content)

    context = read_code_context(tmp_path, "app.py", line=6)  # the "y = 2" line

    assert "def target():" in context
    assert "return x + y" in context
    assert "def outer():" not in context  # only the enclosing function, not siblings


def test_read_code_context_falls_back_for_module_level_line(tmp_path):
    content = "x = 1\ny = 2\nz = 3\n"
    (tmp_path / "app.py").write_text(content)

    context = read_code_context(tmp_path, "app.py", line=2, fallback_context=1)

    assert "y = 2" in context
    assert "x = 1" in context
    assert "z = 3" in context
