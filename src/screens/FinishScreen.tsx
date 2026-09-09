import { Pressable, StyleSheet, Text, View } from "react-native";

export function FinishScreen({ onRematch, onHome }: { onRematch: () => void; onHome: () => void }) {
  return (
    <View style={styles.container}>
      <View>
        <Text style={styles.eyebrow}>NO SCORE. NO WINNER.</Text>
        <Text style={styles.title}>THIS IS{`\n`}MC BATTLE!</Text>
      </View>
      <View style={styles.actions}>
        <Pressable onPress={onRematch} style={styles.rematch}><Text style={styles.rematchText}>REMATCH</Text></Pressable>
        <Pressable onPress={onHome} style={styles.home}><Text style={styles.homeText}>HOME</Text></Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#15151a", justifyContent: "space-between", padding: 28, paddingVertical: 76 },
  eyebrow: { color: "#b3b0ba", fontWeight: "700", fontSize: 12, letterSpacing: 1.5 },
  title: { color: "#f7e900", fontWeight: "900", fontSize: 47, lineHeight: 48, letterSpacing: -2.8, marginTop: 18 },
  actions: { gap: 12 },
  rematch: { alignItems: "center", backgroundColor: "#f7e900", borderRadius: 12, padding: 18 },
  rematchText: { color: "#15151a", fontSize: 16, fontWeight: "900", letterSpacing: 1 },
  home: { alignItems: "center", borderColor: "#54515a", borderRadius: 12, borderWidth: 1, padding: 18 },
  homeText: { color: "#f8f7fa", fontSize: 16, fontWeight: "900", letterSpacing: 1 },
});
