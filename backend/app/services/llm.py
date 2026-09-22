from __future__ import annotations

import json
import logging
from time import perf_counter
from typing import Any

import httpx

from app.core.config import Settings
from app.core.timing import LlmTiming, OllamaRequestTiming
from app.prompts.rappers import build_system_prompt, build_user_prompt

logger = logging.getLogger(__name__)


class LlmError(RuntimeError):
    pass


class OllamaService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def generate_bars(
        self,
        transcript: str,
        history: list[dict[str, Any]],
        rapper_type: str,
        bpm: int,
        is_opening: bool,
        timing: LlmTiming | None = None,
    ) -> list[str]:
        if not self._settings.ollama_model:
            raise LlmError("OLLAMA_MODEL が未設定です。backend/.env を設定してください。")

        messages: list[dict[str, str]] = [
            {"role": "system", "content": build_system_prompt(rapper_type, bpm)},
            {"role": "user", "content": build_user_prompt(transcript, history, is_opening)},
        ]
        for attempt in range(2):
            content = await self._chat(messages, timing)
            bars = self._parse_bars(content)
            if bars is not None:
                return bars
            logger.warning("Ollama returned invalid bars on attempt %s: %r", attempt + 1, content[:300])
            messages.append({"role": "user", "content": "前の出力は無効です。barsが4要素だけのJSONを返してください。"})

        # Keeps the timing pipeline alive after malformed model output. A real
        # connectivity failure still raises LlmError and surfaces in the app.
        return ["ビートの上で返すフレーズ", "響きで切り開くレース", "言葉の芯ならブレず", "この場で鳴らすベース"]

    async def _chat(self, messages: list[dict[str, str]], timing: LlmTiming | None = None) -> str:
        payload = {
            "model": self._settings.ollama_model,
            "messages": messages,
            "stream": False,
            "format": {
                "type": "object",
                "properties": {"bars": {"type": "array", "items": {"type": "string"}, "minItems": 4, "maxItems": 4}},
                "required": ["bars"],
            },
            "options": {"temperature": 0.85},
        }
        request_timing = OllamaRequestTiming(started_at=perf_counter())
        if timing is not None:
            timing.requests.append(request_timing)
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(f"{self._settings.ollama_url}/api/chat", json=payload)
                response.raise_for_status()
                body = response.json()
            request_timing.completed_at = perf_counter()
            if not isinstance(body, dict):
                raise ValueError("Ollama response must be a JSON object")
            self._record_ollama_metrics(request_timing, body)
            return str(body["message"]["content"])
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            logger.exception("Ollama request failed")
            raise LlmError("Ollamaに接続または生成できません。Ollama起動・モデル名を確認してください。") from exc
        finally:
            if request_timing.completed_at is None:
                request_timing.completed_at = perf_counter()

    @staticmethod
    def _record_ollama_metrics(timing: OllamaRequestTiming, body: dict[str, Any]) -> None:
        """Copy optional /api/chat timing fields without assuming their presence."""

        def duration_seconds(name: str) -> float | None:
            value = body.get(name)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return value / 1_000_000_000
            return None

        def token_count(name: str) -> int | None:
            value = body.get(name)
            if isinstance(value, int) and not isinstance(value, bool):
                return value
            return None

        timing.ollama_total_seconds = duration_seconds("total_duration")
        timing.ollama_load_seconds = duration_seconds("load_duration")
        timing.ollama_prompt_eval_seconds = duration_seconds("prompt_eval_duration")
        timing.ollama_eval_seconds = duration_seconds("eval_duration")
        timing.ollama_prompt_tokens = token_count("prompt_eval_count")
        timing.ollama_output_tokens = token_count("eval_count")

    @staticmethod
    def _parse_bars(content: str) -> list[str] | None:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return None
        raw_bars = data.get("bars") if isinstance(data, dict) else None
        if not isinstance(raw_bars, list) or len(raw_bars) != 4:
            return None
        bars = [str(bar).strip() for bar in raw_bars]
        if any(not bar or len(bar) > 70 for bar in bars):
            return None
        return bars
