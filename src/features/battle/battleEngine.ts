import { BattleConfig, BattleState, ChunkRequest } from "./types";
import { BARS_PER_CHUNK, getChunkCount, getRoundCount } from "./timing";

export function createInitialBattleState(config: BattleConfig): BattleState {
  return { actor: config.firstActor, round: 1, chunkIndex: 0, phase: "count-in" };
}

export function getChunkRequest(state: BattleState): ChunkRequest {
  const firstBar = state.chunkIndex * BARS_PER_CHUNK + 1;
  return {
    round: state.round,
    chunkIndex: state.chunkIndex,
    actor: state.actor,
    bars: Array.from({ length: BARS_PER_CHUNK }, (_, index) => firstBar + index),
  };
}

/** Advances only after an entire four-bar chunk has completed. */
export function advanceAfterChunk(state: BattleState, config: BattleConfig): BattleState {
  const chunks = getChunkCount(config.mode);
  if (state.chunkIndex + 1 < chunks) {
    return { ...state, chunkIndex: state.chunkIndex + 1, phase: "count-in" };
  }

  const nextActor = state.actor === "USER" ? "AI" : "USER";
  const endingSecondActor = state.actor !== config.firstActor;
  if (endingSecondActor && state.round === getRoundCount(config.mode)) {
    return { ...state, phase: "finished" };
  }

  return {
    actor: nextActor,
    round: endingSecondActor ? state.round + 1 : state.round,
    chunkIndex: 0,
    phase: "count-in",
  };
}

export function displayBar(state: BattleState): number {
  return state.chunkIndex * BARS_PER_CHUNK + 1;
}
