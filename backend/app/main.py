from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.core.config import settings
from app.core.timing import LlmTiming, SttTiming, TtsBarTiming
from app.models.schemas import HistoryEntry, ProcessChunkResponse
from app.services.llm import LlmError, OllamaService
from app.services.stt import SttError, WhisperService
from app.services.tts import TtsError, TtsService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.generated_audio_dir.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.stt = WhisperService(settings)
    app.state.llm = OllamaService(settings)
    app.state.tts = TtsService(settings)
    logger.info("MC Battle API ready (Whisper=%s, TTS=%s)", settings.whisper_model, settings.tts_engine)
    yield


app = FastAPI(title="MC Battle Local API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # LAN-only MVP; restrict this before exposing beyond the local network.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/generated-audio", StaticFiles(directory=str(settings.generated_audio_dir)), name="generated-audio")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "whisper_model": settings.whisper_model, "tts_engine": settings.tts_engine}


def parse_history(raw_history: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(raw_history)
        if not isinstance(parsed, list):
            raise ValueError("history must be a list")
        entries = [HistoryEntry.model_validate(item) for item in parsed[-12:]]
        return [entry.model_dump() for entry in entries]
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="history_json is invalid") from exc


async def save_upload(upload: UploadFile) -> Path:
    suffix = Path(upload.filename or "chunk.m4a").suffix or ".m4a"
    destination = settings.data_dir / f"{uuid.uuid4()}{suffix}"
    with destination.open("wb") as output:
        while content := await upload.read(1024 * 1024):
            output.write(content)
    return destination


def _format_seconds(seconds: float | None) -> str:
    return f"{seconds:.2f} sec" if seconds is not None else "n/a"


def _append_timing(lines: list[str], label: str, seconds: float | None, indent: str = "  ") -> None:
    lines.append(f"{indent}{label:<44} {_format_seconds(seconds)}")


def _log_process_chunk_timing(
    *,
    request_id: str,
    status: str,
    started_at: float,
    request_setup_seconds: float | None,
    upload_seconds: float | None,
    stt_timing: SttTiming | None,
    stt_wall_seconds: float | None,
    llm_timing: LlmTiming,
    llm_wall_seconds: float | None,
    tts_timings: list[TtsBarTiming],
    tts_wall_seconds: float | None,
    output_setup_seconds: float | None,
    cleanup_seconds: float | None,
) -> None:
    """Emit one complete, request-scoped timing report as a single log record."""

    lines = [
        f"========== PROCESS CHUNK [request={request_id}] ==========",
        f"Status: {status}",
        "",
        "[UPLOAD / PREPROCESS]",
    ]
    if upload_seconds is None:
        lines.append("  skipped (AI opening; no uploaded audio)")
    else:
        _append_timing(lines, "save uploaded file", upload_seconds)
        lines.append("  note: multipart receive completes before this endpoint handler starts")

    lines.extend(["", "[STT]"])
    if stt_timing is None:
        lines.append("  skipped (AI opening; no STT)")
    else:
        model_status = "loaded this request" if stt_timing.model_loaded_this_request else "reused cached model"
        _append_timing(lines, f"model load ({model_status})", stt_timing.model_load_seconds)
        _append_timing(lines, "transcribe setup / decode", stt_timing.transcribe_setup_seconds)
        _append_timing(lines, "segment transcription", stt_timing.segment_transcription_seconds)
        _append_timing(lines, "total (wall-clock)", stt_wall_seconds)

    lines.extend(["", "[LLM / OLLAMA]"])
    if not llm_timing.requests:
        lines.append("  not started")
    for attempt, request_timing in enumerate(llm_timing.requests, start=1):
        started_offset = request_timing.started_at - started_at
        completed_offset = (
            request_timing.completed_at - started_at if request_timing.completed_at is not None else None
        )
        request_wall_seconds = (
            request_timing.completed_at - request_timing.started_at if request_timing.completed_at is not None else None
        )
        _append_timing(lines, f"attempt {attempt} request start (+ from chunk)", started_offset)
        _append_timing(lines, f"attempt {attempt} response received (+ from chunk)", completed_offset)
        _append_timing(lines, f"attempt {attempt} request/generation (wall)", request_wall_seconds)
        if request_timing.ollama_total_seconds is not None:
            _append_timing(lines, f"attempt {attempt} Ollama total duration", request_timing.ollama_total_seconds, "    ")
        if request_timing.ollama_load_seconds is not None:
            _append_timing(lines, f"attempt {attempt} Ollama load duration", request_timing.ollama_load_seconds, "    ")
        if request_timing.ollama_prompt_eval_seconds is not None:
            _append_timing(lines, f"attempt {attempt} prompt eval duration", request_timing.ollama_prompt_eval_seconds, "    ")
        if request_timing.ollama_eval_seconds is not None:
            _append_timing(lines, f"attempt {attempt} generation/eval duration", request_timing.ollama_eval_seconds, "    ")
        if request_timing.ollama_prompt_tokens is not None:
            lines.append(f"    attempt {attempt} prompt tokens              {request_timing.ollama_prompt_tokens}")
        if request_timing.ollama_output_tokens is not None:
            lines.append(f"    attempt {attempt} output tokens              {request_timing.ollama_output_tokens}")
    _append_timing(lines, "total (wall-clock)", llm_wall_seconds)

    lines.extend(["", "[TTS] (4 bars are started concurrently)"])
    for bar_timing in tts_timings:
        _append_timing(lines, f"bar {bar_timing.bar_number} total", bar_timing.total_seconds)
        _append_timing(lines, f"bar {bar_timing.bar_number} engine ({bar_timing.engine})", bar_timing.engine_seconds, "    ")
        if bar_timing.voicevox_audio_query_seconds is not None:
            _append_timing(lines, f"bar {bar_timing.bar_number} VOICEVOX audio_query HTTP", bar_timing.voicevox_audio_query_seconds, "    ")
        if bar_timing.voicevox_synthesis_seconds is not None:
            _append_timing(lines, f"bar {bar_timing.bar_number} VOICEVOX synthesis HTTP", bar_timing.voicevox_synthesis_seconds, "    ")
    _append_timing(lines, "total (wall-clock)", tts_wall_seconds)
    lines.append("  note: per-bar times overlap; do not add them to the TTS total")

    lines.extend(["", "[AUDIO PROCESSING] (inside each concurrent TTS bar)"])
    for bar_timing in tts_timings:
        audio_timing = bar_timing.audio_processing
        _append_timing(lines, f"bar {bar_timing.bar_number} BPM fit total", audio_timing.total_seconds)
        _append_timing(lines, "WAV read", audio_timing.read_wav_seconds, "    ")
        if audio_timing.playback_rate is not None:
            _append_timing(lines, f"speed adjustment ({audio_timing.playback_rate:.2f}x)", audio_timing.speed_adjustment_seconds, "    ")
        else:
            _append_timing(lines, "speed adjustment", audio_timing.speed_adjustment_seconds, "    ")
        if audio_timing.silence_added:
            _append_timing(lines, "silence padding", audio_timing.silence_padding_seconds, "    ")
        else:
            lines.append("    silence padding                    not needed")
        _append_timing(lines, "WAV write", audio_timing.write_wav_seconds, "    ")

    lines.extend(["", "[OTHER]"])
    _append_timing(lines, "request setup / history parse", request_setup_seconds)
    _append_timing(lines, "output directory/file setup", output_setup_seconds)
    _append_timing(lines, "source file cleanup", cleanup_seconds)
    lines.extend(
        [
            "-----------------------------------",
            f"[TOTAL]                            {_format_seconds(perf_counter() - started_at)}",
            "===================================",
        ]
    )
    logger.info("\n%s", "\n".join(lines))


@app.post("/process-chunk", response_model=ProcessChunkResponse)
async def process_chunk(
    history_json: Annotated[str, Form()],
    rapper_type: Annotated[str, Form()],
    bpm: Annotated[int, Form(ge=50, le=220)],
    is_opening: Annotated[bool, Form()],
    audio: Annotated[UploadFile | None, File()] = None,
) -> ProcessChunkResponse:
    """The 4-bar pipeline endpoint: optional audio → STT → Ollama → four TTS WAVs."""
    request_id = uuid.uuid4().hex[:8]
    process_started_at = perf_counter()
    request_setup_started_at = perf_counter()
    history = parse_history(history_json)
    if not is_opening and audio is None:
        raise HTTPException(status_code=422, detail="audio is required unless AI is opening")
    request_setup_seconds = perf_counter() - request_setup_started_at

    source_path: Path | None = None
    upload_seconds: float | None = None
    stt_timing: SttTiming | None = None
    stt_wall_seconds: float | None = None
    llm_timing = LlmTiming()
    llm_wall_seconds: float | None = None
    tts_timings: list[TtsBarTiming] = []
    tts_wall_seconds: float | None = None
    output_setup_seconds: float | None = None
    cleanup_seconds: float | None = None
    status = "in progress"
    transcript = ""

    try:
        if audio is not None:
            upload_started_at = perf_counter()
            source_path = await save_upload(audio)
            upload_seconds = perf_counter() - upload_started_at

            stt_timing = SttTiming()
            stt_started_at = perf_counter()
            transcript = await run_in_threadpool(app.state.stt.transcribe, source_path, stt_timing)
            stt_wall_seconds = perf_counter() - stt_started_at
            logger.info("[request=%s] User chunk transcribed: %s", request_id, transcript)

        llm_started_at = perf_counter()
        bars = await app.state.llm.generate_bars(transcript, history, rapper_type, bpm, is_opening, timing=llm_timing)
        llm_wall_seconds = perf_counter() - llm_started_at

        output_setup_started_at = perf_counter()
        job_id = uuid.uuid4().hex
        output_dir = settings.generated_audio_dir / job_id
        output_dir.mkdir(parents=True, exist_ok=False)
        bar_seconds = 4 * 60 / bpm
        destinations = [output_dir / f"bar-{index + 1}.wav" for index in range(4)]
        tts_timings = [TtsBarTiming(bar_number=index + 1, engine=settings.tts_engine) for index in range(4)]
        output_setup_seconds = perf_counter() - output_setup_started_at

        tts_started_at = perf_counter()
        await asyncio.gather(
            *(
                app.state.tts.synthesize_bar(bar, destination, bar_seconds, timing=timing)
                for bar, destination, timing in zip(bars, destinations, tts_timings)
            )
        )
        tts_wall_seconds = perf_counter() - tts_started_at

        urls = [f"/generated-audio/{job_id}/{destination.name}" for destination in destinations]
        status = "completed"
        return ProcessChunkResponse(transcript=transcript, bars=bars, audio_urls=urls)
    except SttError as exc:
        status = "failed (STT)"
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LlmError as exc:
        status = "failed (LLM / Ollama)"
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TtsError as exc:
        status = "failed (TTS)"
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        status = "failed (unhandled error)"
        logger.exception("Unhandled chunk processing failure")
        raise HTTPException(status_code=500, detail="4小節処理に失敗しました。バックエンドログを確認してください。") from exc
    finally:
        try:
            if source_path is not None:
                cleanup_started_at = perf_counter()
                try:
                    source_path.unlink(missing_ok=True)
                finally:
                    cleanup_seconds = perf_counter() - cleanup_started_at
        finally:
            _log_process_chunk_timing(
                request_id=request_id,
                status=status,
                started_at=process_started_at,
                request_setup_seconds=request_setup_seconds,
                upload_seconds=upload_seconds,
                stt_timing=stt_timing,
                stt_wall_seconds=stt_wall_seconds,
                llm_timing=llm_timing,
                llm_wall_seconds=llm_wall_seconds,
                tts_timings=tts_timings,
                tts_wall_seconds=tts_wall_seconds,
                output_setup_seconds=output_setup_seconds,
                cleanup_seconds=cleanup_seconds,
            )


@app.on_event("shutdown")
async def cleanup_note() -> None:
    # Generated audio intentionally remains available until the process is stopped;
    # it can be inspected during development. It is ignored by git.
    logger.info("MC Battle API stopped")
