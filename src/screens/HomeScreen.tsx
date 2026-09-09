import { Pressable, StyleSheet, Text, View } from "react-native";

export function HomeScreen({ onStart }: { onStart: () => void }) {
  return (
    <View style={styles.container}>
      <View>
        <Text style={styles.eyebrow}>battle stadium</Text>
        <Text style={styles.title}>MC{`\n`}BATTLE</Text>
        <Text style={styles.copy}>らがらがらがら</Text>
      </View>
      <Pressable accessibilityRole="button" onPress={onStart} style={styles.button}>
        <Text style={styles.buttonText}>START BATTLE</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#15151a", justifyContent: "space-between", padding: 28, paddingVertical: 68 },
  eyebrow: { color: "#f7e900", fontWeight: "800", fontSize: 12, letterSpacing: 2 },
  title: { color: "#f8f7fa", fontWeight: "900", fontSize: 68, letterSpacing: -4, lineHeight: 62, marginTop: 18 },
  copy: { color: "#b3b0ba", fontSize: 16, lineHeight: 24, marginTop: 24 },
  button: { alignItems: "center", backgroundColor: "#f7e900", borderRadius: 12, padding: 19 },
  buttonText: { color: "#15151a", fontSize: 16, fontWeight: "900", letterSpacing: 1 },
});
