export type BattleMode = "short" | "long";
export type Actor = "USER" | "AI";
export type FirstActor = Actor;
export type RapperType = "aggressive" | "worldview" | "alliteration" | "rhyme";

export type Beat = {
  id: "boom-bap" | "old-school" | "trap";
  name: string;
  bpm: number;
  /** A future local asset or user-imported file URI. null means metronome-only mode. */
  audioUri: string | null;
};

export type BattleConfig = {
  beat: Beat;
  mode: BattleMode;
  firstActor: FirstActor;
  rapperType: RapperType;
};

export type TurnPhase =
  | "count-in"
  | "recording"
  | "processing"
  | "playing-ai"
  | "waiting-ai"
  | "finished"
  | "error";

export type BattleState = {
  actor: Actor;
  round: number;
  chunkIndex: number;
  phase: TurnPhase;
  errorMessage?: string;
};

export type HistoryEntry = {
  actor: Actor;
  bars: string[];
};

export type ChunkRequest = {
  round: number;
  chunkIndex: number;
  actor: Actor;
  bars: number[];
};

export type ProcessedChunk = {
  transcript: string;
  bars: string[];
  audioUrls: string[];
};
