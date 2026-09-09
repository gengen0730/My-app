import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { battleProgressLabel, useBattleController } from "../features/battle/useBattleController";
import { BattleConfig } from "../features/battle/types";

export function BattleScreen({ config, onFinish, onAbort }: { config: BattleConfig; onFinish: () => void; onAbort: () => void }) {
  const [started, setStarted] = useState(false);
  const controller = useBattleController(config, onFinish);
  const { state, currentBeat, start, stop } = controller;

  useEffect(() => stop, [stop]);

  const begin = async () => {
    setStarted(true);
    await start();
  };

  const phaseLabel: Record<typeof state.phase, string> = {
    "count-in": "COUNT IN",
    recording: "RECORDING",
    processing: "PROCESSING",
    "waiting-ai": "AI PREPARING",
    "playing-ai": "AI RAPPING",
    finished: "FINISHED",
    error: "ERROR",
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.round}>{battleProgressLabel(state, config)}</Text>
        <Pressable onPress={() => { stop(); onAbort(); }}><Text style={styles.abort}>EXIT</Text></Pressable>
      </View>
      <View style={styles.center}>
        <Text style={[styles.actor, state.actor === "USER" ? styles.user : styles.ai]}>{state.actor}</Text>
        <Text style={styles.phase}>{phaseLabel[state.phase]}</Text>
        <View style={styles.beats}>
          {[1, 2, 3, 4].map((beat) => <View key={beat} style={[styles.beat, beat === currentBeat && styles.beatCurrent]} />)}
        </View>
        <Text style={styles.beatText}>{config.beat.name.toUpperCase()} · {config.beat.bpm} BPM</Text>
        <Text style={styles.recording}>{state.phase === "recording" ? "● MIC ON" : "○ MIC OFF"}</Text>
      </View>
      {state.phase === "error" ? <Text style={styles.error}>{state.errorMessage}</Text> : null}
      {!started && state.phase !== "error" ? (
        <Pressable onPress={begin} style={styles.start}><Text style={styles.startText}>TAP TO START</Text></Pressable>
      ) : state.phase === "error" ? (
        <Pressable onPress={begin} style={styles.start}><Text style={styles.startText}>RETRY</Text></Pressable>
      ) : state.phase === "waiting-ai" ? <ActivityIndicator color="#f7e900" size="large" /> : <View style={styles.bottomSpacer} />}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#15151a", padding: 25, paddingTop: 62, justifyContent: "space-between" },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  round: { color: "#aaa6b0", fontSize: 12, fontWeight: "800", letterSpacing: 0.8 },
  abort: { color: "#e28080", fontWeight: "800", fontSize: 12 },
  center: { alignItems: "center", gap: 16 },
  actor: { fontSize: 64, fontWeight: "900", letterSpacing: -3 },
  user: { color: "#f7e900" },
  ai: { color: "#61d8ff" },
  phase: { color: "#f8f7fa", fontSize: 14, letterSpacing: 2, fontWeight: "800" },
  beats: { flexDirection: "row", gap: 13, marginTop: 18 },
  beat: { backgroundColor: "#3b3841", borderRadius: 100, height: 26, width: 26 },
  beatCurrent: { backgroundColor: "#f7e900", transform: [{ scale: 1.18 }] },
  beatText: { color: "#aaa6b0", fontSize: 12, letterSpacing: 1 },
  recording: { color: "#aaa6b0", fontSize: 12, fontWeight: "700", letterSpacing: 1 },
  start: { backgroundColor: "#f7e900", borderRadius: 12, alignItems: "center", padding: 18 },
  startText: { color: "#15151a", fontWeight: "900", letterSpacing: 1 },
  error: { color: "#ff9b9b", fontSize: 14, lineHeight: 21, textAlign: "center" },
  bottomSpacer: { height: 56 },
});
