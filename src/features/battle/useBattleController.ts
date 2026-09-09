import { useCallback, useEffect, useRef, useState } from "react";
import {
  createAudioPlayer,
  RecordingPresets,
  requestRecordingPermissionsAsync,
  setIsAudioActiveAsync,
  setAudioModeAsync,
  useAudioRecorder,
} from "expo-audio";
import { processChunk } from "../../services/api";
import { playBarsAtTempo } from "../../services/audioPlayback";
import { Metronome, startMetronome } from "../../services/metronome";
import { advanceAfterChunk, createInitialBattleState, getChunkRequest } from "./battleEngine";
import { chunkDurationMs, getRoundCount } from "./timing";
import { BattleConfig, BattleState, HistoryEntry, ProcessedChunk } from "./types";

const wait = (milliseconds: number) => new Promise<void>((resolve) => setTimeout(resolve, milliseconds));
const userChunkKey = (round: number, chunkIndex: number) => `user-${round}-${chunkIndex}`;

function answerKeyForAiChunk(current: BattleState, config: BattleConfig): string {
  if (config.firstActor === "AI") {
    return current.round === 1 ? "opening" : userChunkKey(current.round - 1, current.chunkIndex);
  }
  return userChunkKey(current.round, current.chunkIndex);
}

type Controller = {
  state: BattleState;
  currentBeat: number;
  isRunning: boolean;
  start: () => Promise<void>;
  stop: () => void;
};

/**
 * Owns the non-UI battle state machine.  User chunks are sent without awaiting
 * the network request; the pending promise is consumed only when the matching
 * AI chunk reaches its bar head.
 */
export function useBattleController(config: BattleConfig, onFinish: () => void): Controller {
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const [state, setState] = useState<BattleState>(() => createInitialBattleState(config));
  const [currentBeat, setCurrentBeat] = useState(1);
  const runningRef = useRef(false);
  const stateRef = useRef(state);
  const historyRef = useRef<HistoryEntry[]>([]);
  const pendingAiRef = useRef(new Map<string, Promise<ProcessedChunk>>());
  const beatPlayerRef = useRef<ReturnType<typeof createAudioPlayer> | null>(null);
  const metronomeRef = useRef<Metronome | null>(null);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const setPhase = useCallback((phase: BattleState["phase"], errorMessage?: string) => {
    if (!runningRef.current && phase !== "finished" && phase !== "error") return;
    setState((current) => ({ ...current, phase, errorMessage }));
  }, []);

  const submitUserChunk = useCallback(
    (recordingUri: string, current: BattleState) => {
      const key = userChunkKey(current.round, current.chunkIndex);
      const requestHistory = historyRef.current.slice(-12);
      const promise = processChunk({
        recordingUri,
        history: requestHistory,
        rapperType: config.rapperType,
        bpm: config.beat.bpm,
        isOpening: false,
      });
      pendingAiRef.current.set(key, promise);
    },
    [config.beat.bpm, config.rapperType],
  );

  const finish = useCallback(() => {
    runningRef.current = false;
    beatPlayerRef.current?.pause();
    beatPlayerRef.current?.remove();
    beatPlayerRef.current = null;
    metronomeRef.current?.stop();
    metronomeRef.current = null;
    setState((current) => ({ ...current, phase: "finished" }));
    onFinish();
  }, [onFinish]);

  const fail = useCallback((error: unknown) => {
    console.error("Battle engine error", error);
    runningRef.current = false;
    beatPlayerRef.current?.pause();
    beatPlayerRef.current?.remove();
    beatPlayerRef.current = null;
    metronomeRef.current?.stop();
    metronomeRef.current = null;
    const message = error instanceof Error ? error.message : "バトルを続行できません。";
    setState((current) => ({ ...current, phase: "error", errorMessage: message }));
  }, []);

  const runRef = useRef<(next: BattleState) => Promise<void>>(async () => undefined);

  const runUserChunk = useCallback(
    async (current: BattleState) => {
      setState({ ...current, phase: "recording" });
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
      await recorder.prepareToRecordAsync();
      recorder.record();

      const beatMs = 60_000 / config.beat.bpm;
      for (let beat = 1; beat <= 16; beat += 1) {
        if (!runningRef.current) return;
        setCurrentBeat(((beat - 1) % 4) + 1);
        await wait(beatMs);
      }

      if (!runningRef.current) return;
      await recorder.stop();
      const uri = recorder.uri;
      if (!uri) throw new Error("録音ファイルを取得できませんでした。マイク権限を確認してください。");

      // Deliberately not awaited: this is the 4-bar pipeline's parallel stage.
      submitUserChunk(uri, current);
      const next = advanceAfterChunk(current, config);
      if (next.phase === "finished") finish();
      else await runRef.current(next);
    },
    [config, finish, recorder, submitUserChunk],
  );

  const runAiChunk = useCallback(
    async (current: BattleState) => {
      const key = answerKeyForAiChunk(current, config);
      let responsePromise = pendingAiRef.current.get(key);
      if (!responsePromise) {
        // This only occurs for the selected AI-first opener.
        responsePromise = processChunk({
          history: historyRef.current.slice(-12),
          rapperType: config.rapperType,
          bpm: config.beat.bpm,
          isOpening: true,
        });
        pendingAiRef.current.set(key, responsePromise);
      }

      setState({ ...current, phase: "waiting-ai" });
      const response = await responsePromise;
      if (!runningRef.current) return;

      // Keep transcript private: it is passed to later prompts but never drawn.
      const latestUser = response.transcript.trim();
      if (latestUser) historyRef.current.push({ actor: "USER", bars: [latestUser] });
      historyRef.current.push({ actor: "AI", bars: response.bars });
      historyRef.current = historyRef.current.slice(-12);

      setState({ ...current, phase: "playing-ai" });
      await playBarsAtTempo(response.audioUrls, config.beat.bpm);
      if (!runningRef.current) return;

      const next = advanceAfterChunk(current, config);
      if (next.phase === "finished") finish();
      else await runRef.current(next);
    },
    [config, finish],
  );

  useEffect(() => {
    runRef.current = async (next: BattleState) => {
      if (!runningRef.current) return;
      try {
        if (next.actor === "USER") await runUserChunk(next);
        else await runAiChunk(next);
      } catch (error) {
        fail(error);
      }
    };
  }, [fail, runAiChunk, runUserChunk]);

  const start = useCallback(async () => {
    try {
      const permission = await requestRecordingPermissionsAsync();
      if (!permission.granted) throw new Error("マイク権限がありません。設定から許可してください。");
      await setIsAudioActiveAsync(true);
      runningRef.current = true;
      historyRef.current = [];
      pendingAiRef.current.clear();
      metronomeRef.current?.stop();
      metronomeRef.current = startMetronome(config.beat.bpm);
      if (config.beat.audioUri) {
        const player = createAudioPlayer(config.beat.audioUri);
        player.loop = true;
        player.volume = 0.42;
        player.play();
        beatPlayerRef.current = player;
      }
      const initial = createInitialBattleState(config);
      setState(initial);

      // One bar count-in gives the performer a predictable first downbeat.
      setPhase("count-in");
      const beatMs = 60_000 / config.beat.bpm;
      for (let beat = 1; beat <= 4; beat += 1) {
        setCurrentBeat(beat);
        await wait(beatMs);
        if (!runningRef.current) return;
      }
      await runRef.current(initial);
    } catch (error) {
      fail(error);
    }
  }, [config, fail, setPhase]);

  const stop = useCallback(() => {
    runningRef.current = false;
    beatPlayerRef.current?.pause();
    beatPlayerRef.current?.remove();
    beatPlayerRef.current = null;
    metronomeRef.current?.stop();
    metronomeRef.current = null;
    if (recorder.isRecording) recorder.stop().catch((error: unknown) => console.warn("recording stop", error));
  }, [recorder]);

  useEffect(() => stop, [stop]);

  return { state, currentBeat, isRunning: runningRef.current, start, stop };
}

export function battleProgressLabel(state: BattleState, config: BattleConfig): string {
  const bar = state.chunkIndex * 4 + 1;
  const totalBars = config.mode === "short" ? 8 : 16;
  return `ROUND ${state.round}/${getRoundCount(config.mode)} · BAR ${bar}-${Math.min(bar + 3, totalBars)}/${totalBars}`;
}

export function expectedChunkDuration(config: BattleConfig): number {
  return chunkDurationMs(config.beat.bpm);
}
