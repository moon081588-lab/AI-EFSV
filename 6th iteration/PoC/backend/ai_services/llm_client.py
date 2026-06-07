"""Provider-agnostic JSON client for OpenAI-compatible model servers."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from typing import Any

from .config import AI_API_KEY, AI_BASE_URL, AI_PROVIDER, AI_TIMEOUT_SECONDS
from .schemas import AIMetadata, LLMClientResult


def _failure(model_name: str, reason: str) -> LLMClientResult:
    return LLMClientResult(
        data=None,
        metadata=AIMetadata(
            ai_used=False,
            model_name=model_name or None,
            fallback_used=True,
            fallback_reason=reason,
        ),
    )


def _chat_completions_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def _extract_json_content(response_payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(response_payload.get("choices"), list) and response_payload["choices"]:
        choice = response_payload["choices"][0]
        message = choice.get("message", {}) if isinstance(choice, dict) else {}
        content = message.get("content")
    else:
        content = response_payload.get("content", response_payload.get("response"))

    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        raise ValueError("Model response did not contain JSON content.")

    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```JSON").removeprefix("```")
        cleaned = cleaned.removesuffix("```").strip()

    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("Model JSON response must be an object.")
    return parsed


def request_json(
    model_name: str,
    system_prompt: str,
    user_payload: dict[str, Any],
    response_schema: dict[str, Any] | None = None,
) -> LLMClientResult:
    """Call an OpenAI-compatible chat/completions endpoint and return JSON."""

    if not AI_BASE_URL:
        return _failure(model_name, "AI_BASE_URL is not configured.")

    endpoint = _chat_completions_url(AI_BASE_URL)
    response_format = (
        {
            "type": "json_schema",
            "json_schema": {
                "name": "ai_efsv_response",
                "strict": True,
                "schema": response_schema,
            },
        }
        if response_schema
        else {"type": "json_object"}
    )
    request_payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=True)},
        ],
        "response_format": response_format,
        "temperature": 0,
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": f"AI-EFSV/{AI_PROVIDER}",
    }
    if AI_API_KEY:
        headers["Authorization"] = f"Bearer {AI_API_KEY}"

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(request_payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=AI_TIMEOUT_SECONDS) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
        data = _extract_json_content(response_payload)
        return LLMClientResult(
            data=data,
            metadata=AIMetadata(
                ai_used=True,
                model_name=model_name or None,
                fallback_used=False,
                fallback_reason=None,
            ),
        )
    except (TimeoutError, socket.timeout):
        return _failure(model_name, f"AI request timed out after {AI_TIMEOUT_SECONDS} seconds.")
    except urllib.error.HTTPError as exc:
        return _failure(model_name, f"AI endpoint returned HTTP {exc.code}.")
    except urllib.error.URLError as exc:
        return _failure(model_name, f"AI request failed: {exc.reason}.")
    except json.JSONDecodeError:
        return _failure(model_name, "AI endpoint returned invalid JSON.")
    except (ValueError, KeyError, TypeError) as exc:
        return _failure(model_name, f"AI response could not be parsed: {exc}")
    except Exception as exc:
        return _failure(model_name, f"Unexpected AI request failure: {exc}")
