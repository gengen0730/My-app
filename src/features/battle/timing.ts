export const BARS_PER_CHUNK = 4;
export const BEATS_PER_BAR = 4;

export function beatDurationMs(bpm: number): number {
  return 60_000 / bpm;
}

export function barDurationMs(bpm: number): number {
  return BEATS_PER_BAR * beatDurationMs(bpm);
}

export function chunkDurationMs(bpm: number): number {
  return BARS_PER_CHUNK * barDurationMs(bpm);
}

export function getBarsPerTurn(mode: "short" | "long"): number {
  return mode === "short" ? 8 : 16;
}

export function getRoundCount(mode: "short" | "long"): number {
  return mode === "short" ? 4 : 2;
}

export function getChunkCount(mode: "short" | "long"): number {
  return getBarsPerTurn(mode) / BARS_PER_CHUNK;
}

export function clampPlaybackRate(audioDurationSec: number, targetDurationMs: number): number {
  if (!Number.isFinite(audioDurationSec) || audioDurationSec <= 0) return 1;
  const raw = (audioDurationSec * 1000) / targetDurationMs;
  return Math.min(1.35, Math.max(0.8, raw));
}
