from __future__ import annotations

import wave
from pathlib import Path
from time import perf_counter

from app.core.timing import AudioProcessingTiming


class AudioProcessingError(RuntimeError):
    pass


def wav_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as source:
        if source.getframerate() <= 0:
            raise AudioProcessingError("WAV sample rate is invalid")
        return source.getnframes() / source.getframerate()


def fit_wav_to_bar(
    source_path: Path,
    destination_path: Path,
    target_seconds: float,
    timing: AudioProcessingTiming | None = None,
) -> None:
    """Fit a PCM WAV to a bar using conservative 0.8x–1.35x speed adjustment.

    Very short files are padded with silence. Very long files are limited rather
    than radically accelerated; prompt length is the primary duration control.
    """
    started_at = perf_counter()
    try:
        if target_seconds <= 0:
            raise AudioProcessingError("Target bar duration must be positive")

        read_started_at = perf_counter()
        with wave.open(str(source_path), "rb") as source:
            channels = source.getnchannels()
            width = source.getsampwidth()
            frame_rate = source.getframerate()
            compression = source.getcomptype()
            if compression != "NONE" or width not in (1, 2, 3, 4):
                raise AudioProcessingError("Only uncompressed PCM WAV is supported for timing")
            frames = source.readframes(source.getnframes())
            source_duration = len(frames) / (frame_rate * channels * width)
        if timing is not None:
            timing.read_wav_seconds = perf_counter() - read_started_at

        if source_duration <= 0:
            raise AudioProcessingError("TTS produced an empty WAV")

        playback_rate = min(1.35, max(0.8, source_duration / target_seconds))
        if timing is not None:
            timing.playback_rate = playback_rate

        # Re-sample with nearest-neighbour PCM frames, then retain the original WAV
        # header rate. This deliberately dependency-free approach also works on
        # Python 3.13+, where the old audioop module has been removed.
        speed_adjustment_started_at = perf_counter()
        frame_width = channels * width
        source_frames = len(frames) // frame_width
        converted_frames = max(1, int(source_frames / playback_rate))
        source_view = memoryview(frames)
        converted = b"".join(
            source_view[
                min(source_frames - 1, int(index * playback_rate)) * frame_width : min(source_frames, int(index * playback_rate) + 1) * frame_width
            ]
            for index in range(converted_frames)
        )
        if timing is not None:
            timing.speed_adjustment_seconds = perf_counter() - speed_adjustment_started_at

        expected_bytes = int(target_seconds * frame_rate) * channels * width
        if len(converted) < expected_bytes:
            silence_padding_started_at = perf_counter()
            converted += b"\x00" * (expected_bytes - len(converted))
            if timing is not None:
                timing.silence_added = True
                timing.silence_padding_seconds = perf_counter() - silence_padding_started_at

        write_started_at = perf_counter()
        with wave.open(str(destination_path), "wb") as output:
            output.setnchannels(channels)
            output.setsampwidth(width)
            output.setframerate(frame_rate)
            output.writeframes(converted)
        if timing is not None:
            timing.write_wav_seconds = perf_counter() - write_started_at
    finally:
        if timing is not None:
            timing.total_seconds = perf_counter() - started_at
