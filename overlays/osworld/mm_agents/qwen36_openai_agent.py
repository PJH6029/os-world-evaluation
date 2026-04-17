"""Qwen3.6 OpenAI-compatible OSWorld agent overlay.

Provenance:
- Adapted for OSWorld commit e8ba8fde29889ae7e4377f6f325d736818434a04.
- Wraps upstream `mm_agents/qwen3vl_agent.py` instead of copying it, so upstream parsing
  and screenshot prompting stay close to official OSWorld behavior.
"""

from __future__ import annotations

import copy
import os
import time
from typing import Any

import openai

from mm_agents.qwen3vl_agent import Qwen3VLAgent

DEFAULT_MODEL_ID = "Qwen/Qwen3.6-35B-A3B"


class Qwen36OpenAIAgent(Qwen3VLAgent):
    """Qwen3.6 agent that defaults to a local OpenAI-compatible endpoint.

    The parent class already supports OpenAI-compatible chat completions. This
    subclass sets safer defaults and captures the latest request/response so the
    runner can preserve model inputs and raw outputs in per-task trajectories.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("model", os.environ.get("QWEN36_MODEL", DEFAULT_MODEL_ID))
        kwargs.setdefault("api_backend", "openai")
        kwargs.setdefault("temperature", float(os.environ.get("QWEN36_TEMPERATURE", "0")))
        kwargs.setdefault("top_p", float(os.environ.get("QWEN36_TOP_P", "0.9")))
        kwargs.setdefault("max_tokens", int(os.environ.get("QWEN36_MAX_TOKENS", "32768")))
        super().__init__(*args, **kwargs)
        self.last_model_payload: dict[str, Any] | None = None
        self.last_raw_response: str | None = None
        self.last_prediction_error: str | None = None

    def call_llm(self, payload: dict[str, Any], model: str) -> str:  # type: ignore[override]
        self.last_model_payload = copy.deepcopy(payload)
        self.last_prediction_error = None
        try:
            response = super().call_llm(payload, model)
        except Exception as exc:  # noqa: BLE001 - preserve raw endpoint failure for trajectory
            self.last_prediction_error = repr(exc)
            raise
        self.last_raw_response = response
        return response


    def _call_llm_openai(self, messages: list[dict[str, Any]], model: str) -> str:  # type: ignore[override]
        """Call OpenAI-compatible endpoint while enforcing configured decoding.

        Upstream OSWorld's Qwen3VL OpenAI path intentionally comments out
        temperature/top_p. This overlay sends them explicitly so run manifests and
        actual requests agree.
        """
        base_url = os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:8000/v1")
        api_key = os.environ.get("OPENAI_API_KEY", "EMPTY")
        client = openai.OpenAI(base_url=base_url, api_key=api_key)
        last_error: Exception | None = None
        for _attempt in range(1, 6):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    top_p=self.top_p,
                )
                return response.choices[0].message.content or ""
            except Exception as exc:  # noqa: BLE001 - preserve endpoint failures through caller
                last_error = exc
                if _attempt < 5:
                    time.sleep(5)
                    continue
        if last_error:
            raise last_error
        return ""

    def reset(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        super().reset(*args, **kwargs)
        self.last_model_payload = None
        self.last_raw_response = None
        self.last_prediction_error = None
