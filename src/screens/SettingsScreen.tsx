import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { ChoiceRow } from "../components/ChoiceRow";
import { BEATS } from "../features/battle/beats";
import { BattleConfig, BattleMode, FirstActor, RapperType } from "../features/battle/types";

type Props = {
  config: BattleConfig;
  onChange: (config: BattleConfig) => void;
  onStart: () => void;
  onBack: () => void;
};

const rapperChoices: { value: RapperType; label: string }[] = [
  { value: "aggressive", label: "喧嘩系" },
  { value: "worldview", label: "アンサー少なめ" },
  { value: "alliteration", label: "頭韻系" },
  { value: "rhyme", label: "脚韻系" },
];

export function SettingsScreen({ config, onChange, onStart, onBack }: Props) {
  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Pressable onPress={onBack} style={styles.back}><Text style={styles.backText}>← HOME</Text></Pressable>
      <Text style={styles.title}>BATTLE SETTINGS</Text>
      <View style={styles.content}>
        <ChoiceRow
          label="BEAT"
          value={config.beat.id}
          choices={BEATS.map((beat) => ({ value: beat.id, label: `${beat.name} / ${beat.bpm} BPM` }))}
          onChange={(id) => onChange({ ...config, beat: BEATS.find((beat) => beat.id === id) ?? config.beat })}
        />
        <ChoiceRow<BattleMode>
          label="FORMAT"
          value={config.mode}
          choices={[{ value: "short", label: "8 BARS × 4" }, { value: "long", label: "16 BARS × 2" }]}
          onChange={(mode) => onChange({ ...config, mode })}
        />
        <ChoiceRow<FirstActor>
          label="FIRST"
          value={config.firstActor}
          choices={[{ value: "USER", label: "USER FIRST" }, { value: "AI", label: "AI FIRST" }]}
          onChange={(firstActor) => onChange({ ...config, firstActor })}
        />
        <ChoiceRow<RapperType>
          label="AI RAPPER"
          value={config.rapperType}
          choices={rapperChoices}
          onChange={(rapperType) => onChange({ ...config, rapperType })}
        />
      </View>
      <Text style={styles.note}>音源を assets/beats に追加するまで、BPMタイミング表示で進行します。</Text>
      <Pressable onPress={onStart} style={styles.start}><Text style={styles.startText}>START</Text></Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { backgroundColor: "#15151a", flexGrow: 1, padding: 24, paddingTop: 62, paddingBottom: 34 },
  back: { alignSelf: "flex-start", paddingVertical: 8 },
  backText: { color: "#b3b0ba", fontSize: 13, fontWeight: "700" },
  title: { color: "#f8f7fa", fontSize: 28, fontWeight: "900", marginTop: 16, letterSpacing: -0.8 },
  content: { gap: 26, marginTop: 32 },
  note: { color: "#77737c", fontSize: 12, lineHeight: 18, marginTop: 26 },
  start: { alignItems: "center", backgroundColor: "#f7e900", borderRadius: 12, marginTop: 24, padding: 18 },
  startText: { color: "#15151a", fontSize: 16, fontWeight: "900", letterSpacing: 1 },
});
