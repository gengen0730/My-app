from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import httpx

from app.core.config import Settings
from app.services.audio import fit_wav_to_bar

logger = logging.getLogger(__name__)


class TtsError(RuntimeError):
    pass


class TtsService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def synthesize_bar(self, text: str, destination: Path, target_seconds: float) -> None:
        raw_path = destination.with_name(f"{destination.stem}.raw.wav")
        if self._settings.tts_engine == "voicevox":
            await self._voicevox(text, raw_path)
        elif self._settings.tts_engine == "pyttsx3":
            await asyncio.to_thread(self._pyttsx3, text, raw_path)
        else:
            raise TtsError("TTS_ENGINE は voicevox または pyttsx3 を指定してください。")

        try:
            await asyncio.to_thread(fit_wav_to_bar, raw_path, destination, target_seconds)
        except Exception as exc:
            logger.exception("TTS bar timing adjustment failed")
            raise TtsError("TTS音声の小節同期に失敗しました。") from exc
        finally:
            raw_path.unlink(missing_ok=True)

    async def _voicevox(self, text: str, destination: Path) -> None:
        params = {"text": text, "speaker": self._settings.voicevox_speaker_id}
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                query = await client.post(f"{self._settings.voicevox_url}/audio_query", params=params)
                query.raise_for_status()
                speech = await client.post(
                    f"{self._settings.voicevox_url}/synthesis",
                    params={"speaker": self._settings.voicevox_speaker_id},
                    json=query.json(),
                )
                speech.raise_for_status()
            destination.write_bytes(speech.content)
        except httpx.HTTPError as exc:
            logger.exception("VOICEVOX request failed")
            raise TtsError("VOICEVOX Engineに接続できません。起動状態とURLを確認してください。") from exc

    def _pyttsx3(self, text: str, destination: Path) -> None:
        try:
            import pyttsx3
        except ImportError as exc:
            raise TtsError("pyttsx3 が未インストールです。") from exc
        try:
            engine = pyttsx3.init()
            if self._settings.pyttsx3_voice_id:
                engine.setProperty("voice", self._settings.pyttsx3_voice_id)
            engine.save_to_file(text, str(destination))
            engine.runAndWait()
        except Exception as exc:
            logger.exception("pyttsx3 request failed")
            raise TtsError("pyttsx3の音声生成に失敗しました。") from exc
