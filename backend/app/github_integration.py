import os
import subprocess
import tempfile
from pathlib import Path

import requests

from app.correlation import find_repo_root
from app.crypto import CryptoNotConfigured, decrypt_secret
from app.models import FixSuggestionRecord, Issue, Project

GITHUB_API = "https://api.github.com"

# The correlation step (see correlation.py) always runs git blame inside
# this checkout — it's the one repo this whole system watches, so it's
# also the only repo a PR can be opened against. A multi-repo version
# would need Issue to carry which local checkout it came from.
DEMO_REPO_PATH = os.environ.get("DEMO_REPO_PATH", str(Path(__file__).resolve().parents[2] / "data" / "demo-repo"))


class GitHubIntegrationError(Exception):
    pass


def _run(args: list, cwd: Path) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise GitHubIntegrationError(f"`{' '.join(args)}` failed: {result.stderr.strip()}")
    return result.stdout


def open_pull_request(
    project: Project,
    issue: Issue,
    fix_suggestion: FixSuggestionRecord,
    base_branch: str = "main",
) -> str:
    """Applies the LLM-suggested diff on a fresh branch, pushes it, and
    opens a PR — the actual code change still goes through GitHub's normal
    PR review/merge flow, so nothing is auto-applied to the target branch.
    See CLAUDE.md: "No LLM-generated fix is ever auto-applied — always a
    proposed diff requiring human approval." The PR *is* that proposal;
    merging it is the approval."""
    if not project.github_repo:
        raise GitHubIntegrationError("No GitHub repo configured for this project")
    if not project.github_token_encrypted:
        raise GitHubIntegrationError("No GitHub token configured for this project")

    try:
        token = decrypt_secret(project.github_token_encrypted)
    except CryptoNotConfigured as exc:
        raise GitHubIntegrationError(str(exc)) from exc

    repo_root = find_repo_root(Path(DEMO_REPO_PATH))
    branch = f"logtofix/issue-{str(issue.id)[:8]}"

    _run(["git", "fetch", "origin", base_branch], repo_root)
    _run(["git", "checkout", "-B", branch, f"origin/{base_branch}"], repo_root)

    with tempfile.NamedTemporaryFile("w", suffix=".diff", delete=False) as f:
        f.write(fix_suggestion.diff)
        diff_path = f.name
    try:
        _run(["git", "apply", "--whitespace=fix", diff_path], repo_root)
    except GitHubIntegrationError:
        _run(["git", "checkout", base_branch], repo_root)
        _run(["git", "branch", "-D", branch], repo_root)
        raise
    finally:
        os.unlink(diff_path)

    _run(["git", "commit", "-am", f"Fix: {issue.title[:72]}\n\n{fix_suggestion.explanation}"], repo_root)

    push_url = f"https://x-access-token:{token}@github.com/{project.github_repo}.git"
    try:
        _run(["git", "push", push_url, f"{branch}:{branch}", "-f"], repo_root)
    finally:
        _run(["git", "checkout", base_branch], repo_root)

    response = requests.post(
        f"{GITHUB_API}/repos/{project.github_repo}/pulls",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        json={
            "title": f"Fix: {issue.title[:72]}",
            "head": branch,
            "base": base_branch,
            "body": (
                f"{fix_suggestion.explanation}\n\n"
                f"Confidence: {fix_suggestion.confidence:.0%}\n\n"
                "_Opened automatically by Log-to-Fix — please review before merging._"
            ),
        },
        timeout=15,
    )
    if response.status_code >= 400:
        raise GitHubIntegrationError(f"GitHub API error {response.status_code}: {response.text}")

    return response.json()["html_url"]
