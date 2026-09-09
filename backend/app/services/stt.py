from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import Settings

logger = logging.getLogger(__name__)


class SttError(RuntimeError):
    pass


class WhisperService:
    """Lazy model loading keeps FastAPI startup quick and avoids cloud APIs."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise SttError("faster-whisper が未インストールです。requirements.txt をインストールしてください。") from exc
            logger.info("Loading faster-whisper model: %s", self._settings.whisper_model)
            self._model = WhisperModel(
                self._settings.whisper_model,
                device=self._settings.whisper_device,
                compute_type=self._settings.whisper_compute_type,
            )
        return self._model

    def transcribe(self, audio_path: Path) -> str:
        try:
            segments, info = self._get_model().transcribe(
                str(audio_path),
                language=None,
                beam_size=1,
                vad_filter=True,
                condition_on_previous_text=False,
            )
            text = " ".join(segment.text.strip() for segment in segments).strip()
            logger.info("STT complete language=%s chars=%d", info.language, len(text))
            return text
        except SttError:
            raise
        except Exception as exc:
            logger.exception("Whisper transcription failed")
            raise SttError("Whisper の文字起こしに失敗しました。入力音声形式とモデル設定を確認してください。") from exc
