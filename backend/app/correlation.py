import re
import subprocess
from pathlib import Path
from typing import Optional

# Matches a standard Python traceback frame line, e.g.:
#   File "/path/to/app.py", line 64, in get_order
FRAME_PATTERN = re.compile(r'File "(?P<file>[^"]+)", line (?P<line>\d+)')


def find_repo_root(start: Path) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=start, capture_output=True, text=True, check=True,
    )
    return Path(result.stdout.strip())


def extract_last_matching_frame(stack_trace: str, path_filter: str) -> Optional[tuple]:
    """Returns the deepest (last) traceback frame whose file path contains
    path_filter — i.e. the innermost frame that's actually in the monitored
    repo, skipping stdlib/library frames above it."""
    frames = FRAME_PATTERN.findall(stack_trace)
    matching = [(f, int(l)) for f, l in frames if path_filter in f]
    return matching[-1] if matching else None


def blame_line(repo_root: Path, file_path: str, line: int) -> Optional[dict]:
    try:
        rel_path = Path(file_path).resolve().relative_to(repo_root)
    except ValueError:
        # Resolved path escapes the repo root — refuse rather than blame an
        # arbitrary file on disk (stack traces are log content, not fully
        # trusted input).
        return None

    result = subprocess.run(
        ["git", "blame", "-L", f"{line},{line}", "--porcelain", str(rel_path)],
        cwd=repo_root, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    return _parse_porcelain(result.stdout, str(rel_path), line)


def _parse_porcelain(output: str, file_path: str, line: int) -> Optional[dict]:
    lines = output.splitlines()
    if not lines:
        return None
    commit_hash = lines[0].split()[0]
    author = next((l.split(" ", 1)[1] for l in lines if l.startswith("author ")), None)
    summary = next((l.split(" ", 1)[1] for l in lines if l.startswith("summary ")), None)
    author_time = next((l.split(" ", 1)[1] for l in lines if l.startswith("author-time ")), None)
    return {
        "commit": commit_hash,
        "author": author,
        "summary": summary,
        "author_time": author_time,
        "file": file_path,
        "line": line,
    }


def correlate_error_to_commit(stack_trace: str, path_filter: str = "demo-repo") -> Optional[dict]:
    """Given a Python traceback string, find the responsible commit via git
    blame. Returns None if there's no stack trace, no frame matching
    path_filter, or the file isn't tracked in git (e.g. uncommitted)."""
    if not stack_trace:
        return None

    frame = extract_last_matching_frame(stack_trace, path_filter)
    if frame is None:
        return None

    file_path, line = frame
    try:
        repo_root = find_repo_root(Path(file_path).parent)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    return blame_line(repo_root, file_path, line)
