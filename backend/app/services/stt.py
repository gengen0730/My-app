from __future__ import annotations

import logging
from pathlib import Path
from time import perf_counter

from app.core.config import Settings
from app.core.timing import SttTiming

logger = logging.getLogger(__name__)


class SttError(RuntimeError):
    pass


class WhisperService:
    """Lazy model loading keeps FastAPI startup quick and avoids cloud APIs."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model = None

    def _get_model(self, timing: SttTiming | None = None):
        if self._model is None:
            model_load_started = perf_counter()
            try:
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
            finally:
                if timing is not None:
                    timing.model_loaded_this_request = True
                    timing.model_load_seconds = perf_counter() - model_load_started
        return self._model

    def transcribe(self, audio_path: Path, timing: SttTiming | None = None) -> str:
        started_at = perf_counter()
        try:
            model = self._get_model(timing)

            # faster-whisper performs input decoding and setup before returning
            # its lazy segment iterator. Actual transcription continues while
            # that iterator is consumed below, so keep both measurements.
            transcribe_setup_started = perf_counter()
            segments, info = model.transcribe(
                str(audio_path),
                language=None,
                beam_size=1,
                vad_filter=True,
                condition_on_previous_text=False,
            )
            if timing is not None:
                timing.transcribe_setup_seconds = perf_counter() - transcribe_setup_started

            segment_transcription_started = perf_counter()
            text = " ".join(segment.text.strip() for segment in segments).strip()
            if timing is not None:
                timing.segment_transcription_seconds = perf_counter() - segment_transcription_started
            logger.info("STT complete language=%s chars=%d", info.language, len(text))
            return text
        except SttError:
            raise
        except Exception as exc:
            logger.exception("Whisper transcription failed")
            raise SttError("Whisper の文字起こしに失敗しました。入力音声形式とモデル設定を確認してください。") from exc
        finally:
            if timing is not None:
                timing.total_seconds = perf_counter() - started_at
