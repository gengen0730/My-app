from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    whisper_model: str = os.getenv("WHISPER_MODEL", "base")
    whisper_device: str = os.getenv("WHISPER_DEVICE", "cpu")
    whisper_compute_type: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    ollama_url: str = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "")
    tts_engine: str = os.getenv("TTS_ENGINE", "voicevox").lower()
    voicevox_url: str = os.getenv("VOICEVOX_URL", "http://127.0.0.1:50021").rstrip("/")
    voicevox_speaker_id: int = int(os.getenv("VOICEVOX_SPEAKER_ID", "3"))
    pyttsx3_voice_id: str = os.getenv("PYTTSX3_VOICE_ID", "")
    data_dir: Path = BACKEND_ROOT / "data"
    generated_audio_dir: Path = BACKEND_ROOT / "generated_audio"


settings = Settings()
