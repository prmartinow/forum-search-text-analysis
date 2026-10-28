"""Gemini Bridge client wrapper with retry logic and JSON response normalization."""

import json
import logging
import time
from typing import Any, Dict, List
from openai import OpenAI

from extractor.config import config
from extractor.prompt import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_JSON_FORMAT_DESCRIPTION

logger = logging.getLogger(__name__)

class GeminiBridgeClient:
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or config.gemini_bridge_url
        self.model = model or config.model
        self.client = OpenAI(
            base_url=self.base_url,
            api_key='dummy'  # Gemini Bridge manages Google OAuth tokens internally
        )

    def extract_batch(self, posts_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send a batch of posts to Gemini Bridge for multi-layer extraction.
        """
        user_content = (
            f"Please extract Layer A, B, C, and D intelligence from the following {len(posts_batch)} posts.\n"
            f"Required JSON structure:\n{EXTRACTION_JSON_FORMAT_DESCRIPTION}\n\n"
            f"Posts to analyze:\n" + json.dumps(posts_batch, indent=2, ensure_ascii=False)
        )

        messages = [
            {'role': 'system', 'content': EXTRACTION_SYSTEM_PROMPT},
            {'role': 'user', 'content': user_content}
        ]

        last_error = None
        for attempt in range(1, config.max_retries + 1):
            try:
                t0 = time.time()
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={'type': 'json_object'},
                    temperature=config.temperature,
                )
                duration = time.time() - t0

                raw_content = response.choices[0].message.content
                if not raw_content or not raw_content.strip():
                    raise ValueError("Upstream model returned empty completion (filtered or empty candidate)")

                parsed_json = json.loads(raw_content)

                usage = getattr(response, 'usage', None)
                prompt_tokens = usage.prompt_tokens if usage else 0
                completion_tokens = usage.completion_tokens if usage else 0

                return {
                    'success': True,
                    'data': parsed_json,
                    'raw_json': raw_content,
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'duration': duration,
                    'model': self.model
                }

            except Exception as exc:
                last_error = exc
                if "empty completion" in str(exc).lower():
                    # Upstream safety filter or empty candidate; break immediately to isolate
                    break
                logger.warning(
                    f"Attempt {attempt}/{config.max_retries} failed on Gemini Bridge: {exc}"
                )
                if attempt < config.max_retries:
                    backoff = (2 ** attempt) + config.rate_limit_delay
                    time.sleep(backoff)

        raise RuntimeError(
            f"Extraction attempt failed. Last error: {last_error}"
        )
