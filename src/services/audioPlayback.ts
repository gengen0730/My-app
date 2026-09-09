import { createAudioPlayer, setAudioModeAsync } from "expo-audio";
import { barDurationMs, clampPlaybackRate } from "../features/battle/timing";

const wait = (milliseconds: number) => new Promise<void>((resolve) => setTimeout(resolve, milliseconds));

/**
 * Starts one pre-generated TTS file at every bar head.  The backend already
 * makes each WAV close to a bar; this small client correction avoids drift.
 */
export async function playBarsAtTempo(audioUrls: string[], bpm: number): Promise<void> {
  await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true });
  const targetMs = barDurationMs(bpm);

  for (const url of audioUrls) {
    const player = createAudioPlayer(url);
    // Native duration becomes available shortly after source creation.  Falling
    // back to 1 keeps playback safe if a platform has not loaded metadata yet.
    await wait(80);
    player.playbackRate = clampPlaybackRate(player.duration, targetMs);
    player.shouldCorrectPitch = true;
    player.play();
    await wait(targetMs);
    player.pause();
    player.remove();
  }
}
