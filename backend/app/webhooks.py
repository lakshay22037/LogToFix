import logging

import requests

from app.models import Issue, Project

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT_SECONDS = 5


def notify_new_issue(project: Project, issue: Issue) -> None:
    """Fires a Slack-compatible {"text": ...} payload at the project's
    configured webhook on a newly created issue — deliberately generic
    (not the Slack SDK) so it also works with any other webhook-shaped
    endpoint (e.g. a test URL from webhook.site). Best-effort: a failed
    notification never fails the ingestion pipeline."""
    if not project.webhook_url:
        return

    text = (
        f":rotating_light: New issue in *{project.name}*: {issue.title}\n"
        f"Service: `{issue.service}` · Level: `{issue.level}`"
        + (f" · Commit: `{issue.commit_hash[:8]}`" if issue.commit_hash else "")
    )
    try:
        requests.post(project.webhook_url, json={"text": text}, timeout=WEBHOOK_TIMEOUT_SECONDS)
    except requests.exceptions.RequestException:
        logger.exception("Failed to deliver webhook notification for project %s", project.id)
