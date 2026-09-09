import { HistoryEntry, ProcessedChunk, RapperType } from "../features/battle/types";

const apiBaseUrl = process.env.EXPO_PUBLIC_API_BASE_URL?.replace(/\/$/, "");

type ProcessChunkPayload = {
  recordingUri?: string;
  history: HistoryEntry[];
  rapperType: RapperType;
  bpm: number;
  isOpening: boolean;
};

type ApiProcessedChunk = {
  transcript: string;
  bars: string[];
  audio_urls: string[];
};

function requireApiBaseUrl(): string {
  if (!apiBaseUrl) {
    throw new Error("EXPO_PUBLIC_API_BASE_URL が未設定です。.env を確認してください。");
  }
  return apiBaseUrl;
}

function absoluteUrl(url: string): string {
  if (/^https?:\/\//.test(url)) return url;
  return `${requireApiBaseUrl()}${url.startsWith("/") ? "" : "/"}${url}`;
}

export async function processChunk(payload: ProcessChunkPayload): Promise<ProcessedChunk> {
  const baseUrl = requireApiBaseUrl();
  const form = new FormData();
  form.append("history_json", JSON.stringify(payload.history.slice(-12)));
  form.append("rapper_type", payload.rapperType);
  form.append("bpm", String(payload.bpm));
  form.append("is_opening", String(payload.isOpening));

  if (payload.recordingUri) {
    const filename = payload.recordingUri.split("/").pop() ?? "chunk.m4a";
    if (typeof window !== "undefined") {
      // React Native accepts the { uri, name, type } shape below, but web
      // serializes that object as "[object Object]". Read the blob URL first
      // so the browser sends an actual multipart file.
      const audioResponse = await fetch(payload.recordingUri);
      if (!audioResponse.ok) {
        throw new Error("録音ファイルを読み込めませんでした。もう一度録音してください。");
      }
      const audio = await audioResponse.blob();
      form.append("audio", audio, filename);
    } else {
      form.append("audio", {
        uri: payload.recordingUri,
        name: filename,
        type: "audio/m4a",
      } as unknown as Blob);
    }
  }

  let response: Response;
  try {
    response = await fetch(`${baseUrl}/process-chunk`, { method: "POST", body: form });
  } catch (error) {
    console.error("FastAPI connection failed", error);
    throw new Error("PC上のFastAPIに接続できません。同じWi-FiとIP設定を確認してください。");
  }

  if (!response.ok) {
    const detail = await response.text();
    console.error("process-chunk failed", response.status, detail);
    throw new Error("AI処理に失敗しました。FastAPI / Ollama / TTS のログを確認してください。");
  }

  const data = (await response.json()) as ApiProcessedChunk;
  if (data.bars.length !== 4 || data.audio_urls.length !== 4) {
    throw new Error("AIから不正な4小節レスポンスが返りました。");
  }

  return {
    transcript: data.transcript,
    bars: data.bars,
    audioUrls: data.audio_urls.map(absoluteUrl),
  };
}
