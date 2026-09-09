import { Beat } from "./types";

/**
 * Keep beat metadata separate from the engine. Add audio files under assets/beats
 * and set audioUri here (or inject a file URI after an import feature is added).
 */
export const BEATS: Beat[] = [
  { id: "boom-bap", name: "Boom Bap", bpm: 90, audioUri: null },
  { id: "old-school", name: "Old School", bpm: 100, audioUri: null },
  { id: "trap", name: "Trap", bpm: 120, audioUri: null },
];
