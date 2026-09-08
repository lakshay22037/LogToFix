import logging
from typing import Optional

from llm_core.client import ClaudeClient, LLMClient
from llm_core.prompts import SYSTEM_PROMPT, build_user_prompt
from llm_core.schemas import FixSuggestion

logger = logging.getLogger(__name__)


def suggest_fix(
    message: str,
    stack_trace: str,
    correlation: dict,
    code_context: str,
    client: Optional[LLMClient] = None,
) -> FixSuggestion:
    client = client or ClaudeClient()
    user_prompt = build_user_prompt(message, stack_trace, correlation, code_context)

    # Every LLM request/response is logged for later evaluation and
    # debugging (see ENGINEERING_STANDARDS.md §3).
    logger.info("LLM request | system=%s | user=%s", SYSTEM_PROMPT, user_prompt)
    suggestion = client.suggest_fix(SYSTEM_PROMPT, user_prompt)
    logger.info("LLM response: %s", suggestion.model_dump())
    return suggestion
