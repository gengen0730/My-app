import { Pressable, StyleSheet, Text, View } from "react-native";

export type Choice<T extends string> = { value: T; label: string; description?: string };

type Props<T extends string> = {
  label: string;
  value: T;
  choices: Choice<T>[];
  onChange: (value: T) => void;
};

export function ChoiceRow<T extends string>({ label, value, choices, onChange }: Props<T>) {
  return (
    <View style={styles.group}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.choices}>
        {choices.map((choice) => {
          const selected = choice.value === value;
          return (
            <Pressable
              accessibilityRole="radio"
              accessibilityState={{ selected }}
              key={choice.value}
              onPress={() => onChange(choice.value)}
              style={[styles.choice, selected && styles.choiceSelected]}
            >
              <Text style={[styles.choiceTitle, selected && styles.choiceTitleSelected]}>{choice.label}</Text>
              {choice.description ? <Text style={styles.choiceDescription}>{choice.description}</Text> : null}
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  group: { gap: 8 },
  label: { color: "#b3b0ba", fontSize: 12, fontWeight: "700", letterSpacing: 1.2 },
  choices: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  choice: { borderWidth: 1, borderColor: "#34333d", borderRadius: 12, paddingHorizontal: 12, paddingVertical: 10 },
  choiceSelected: { backgroundColor: "#f7e900", borderColor: "#f7e900" },
  choiceTitle: { color: "#f5f2f7", fontSize: 14, fontWeight: "700" },
  choiceTitleSelected: { color: "#15151a" },
  choiceDescription: { color: "#9f9ba6", fontSize: 10, marginTop: 3 },
});
