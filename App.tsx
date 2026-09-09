import { useState } from "react";
import { StatusBar } from "expo-status-bar";
import { SafeAreaView, StyleSheet } from "react-native";
import { BEATS } from "./src/features/battle/beats";
import { BattleConfig } from "./src/features/battle/types";
import { BattleScreen } from "./src/screens/BattleScreen";
import { FinishScreen } from "./src/screens/FinishScreen";
import { HomeScreen } from "./src/screens/HomeScreen";
import { SettingsScreen } from "./src/screens/SettingsScreen";

type Screen = "home" | "settings" | "battle" | "finish";

const initialConfig: BattleConfig = {
  beat: BEATS[0],
  mode: "short",
  firstActor: "USER",
  rapperType: "rhyme",
};

export default function App() {
  const [screen, setScreen] = useState<Screen>("home");
  const [config, setConfig] = useState<BattleConfig>(initialConfig);

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="light" />
      {screen === "home" ? <HomeScreen onStart={() => setScreen("settings")} /> : null}
      {screen === "settings" ? <SettingsScreen config={config} onChange={setConfig} onBack={() => setScreen("home")} onStart={() => setScreen("battle")} /> : null}
      {screen === "battle" ? <BattleScreen config={config} onFinish={() => setScreen("finish")} onAbort={() => setScreen("settings")} /> : null}
      {screen === "finish" ? <FinishScreen onRematch={() => setScreen("battle")} onHome={() => setScreen("home")} /> : null}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({ safeArea: { flex: 1, backgroundColor: "#15151a" } });
