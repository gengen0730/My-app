from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.core.config import settings
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


@app.post("/process-chunk", response_model=ProcessChunkResponse)
async def process_chunk(
    history_json: Annotated[str, Form()],
    rapper_type: Annotated[str, Form()],
    bpm: Annotated[int, Form(ge=50, le=220)],
    is_opening: Annotated[bool, Form()],
    audio: Annotated[UploadFile | None, File()] = None,
) -> ProcessChunkResponse:
    """The 4-bar pipeline endpoint: optional audio → STT → Ollama → four TTS WAVs."""
    history = parse_history(history_json)
    if not is_opening and audio is None:
        raise HTTPException(status_code=422, detail="audio is required unless AI is opening")

    source_path: Path | None = None
    transcript = ""
    try:
        if audio is not None:
            source_path = await save_upload(audio)
            transcript = await run_in_threadpool(app.state.stt.transcribe, source_path)
            logger.info("User chunk transcribed: %s", transcript)

        bars = await app.state.llm.generate_bars(transcript, history, rapper_type, bpm, is_opening)
        job_id = uuid.uuid4().hex
        output_dir = settings.generated_audio_dir / job_id
        output_dir.mkdir(parents=True, exist_ok=False)
        bar_seconds = 4 * 60 / bpm
        destinations = [output_dir / f"bar-{index + 1}.wav" for index in range(4)]
        await asyncio.gather(
            *(app.state.tts.synthesize_bar(bar, destination, bar_seconds) for bar, destination in zip(bars, destinations))
        )
        urls = [f"/generated-audio/{job_id}/{destination.name}" for destination in destinations]
        return ProcessChunkResponse(transcript=transcript, bars=bars, audio_urls=urls)
    except SttError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LlmError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TtsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unhandled chunk processing failure")
        raise HTTPException(status_code=500, detail="4小節処理に失敗しました。バックエンドログを確認してください。") from exc
    finally:
        if source_path is not None:
            source_path.unlink(missing_ok=True)


@app.on_event("shutdown")
async def cleanup_note() -> None:
    # Generated audio intentionally remains available until the process is stopped;
    # it can be inspected during development. It is ignored by git.
    logger.info("MC Battle API stopped")
