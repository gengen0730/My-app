from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SttTiming:
    """Per-request measurements collected inside the synchronous STT service."""

    model_loaded_this_request: bool = False
    model_load_seconds: float = 0.0
    transcribe_setup_seconds: float | None = None
    segment_transcription_seconds: float | None = None
    total_seconds: float | None = None


@dataclass
class OllamaRequestTiming:
    """Wall-clock and server-reported timings for one /api/chat request."""

    started_at: float
    completed_at: float | None = None
    ollama_total_seconds: float | None = None
    ollama_load_seconds: float | None = None
    ollama_prompt_eval_seconds: float | None = None
    ollama_eval_seconds: float | None = None
    ollama_prompt_tokens: int | None = None
    ollama_output_tokens: int | None = None


@dataclass
class LlmTiming:
    requests: list[OllamaRequestTiming] = field(default_factory=list)


@dataclass
class AudioProcessingTiming:
    """Measurements made while a raw WAV is fitted to one bar."""

    read_wav_seconds: float | None = None
    speed_adjustment_seconds: float | None = None
    silence_padding_seconds: float | None = None
    write_wav_seconds: float | None = None
    total_seconds: float | None = None
    playback_rate: float | None = None
    silence_added: bool = False


@dataclass
class TtsBarTiming:
    """Per-bar timings. Each instance belongs to exactly one asyncio task."""

    bar_number: int
    engine: str
    engine_seconds: float | None = None
    voicevox_audio_query_seconds: float | None = None
    voicevox_synthesis_seconds: float | None = None
    audio_processing: AudioProcessingTiming = field(default_factory=AudioProcessingTiming)
    total_seconds: float | None = None
