export type Metronome = {
  stop: () => void;
};

const silentMetronome: Metronome = { stop: () => undefined };

/**
 * A click track scheduled against the Web Audio clock.  Keeping a short
 * look-ahead window avoids the drift that accumulates with setTimeout alone.
 */
export function startMetronome(bpm: number): Metronome {
  if (typeof window === "undefined") return silentMetronome;

  const browserWindow = window as Window & { webkitAudioContext?: typeof AudioContext };
  const AudioContextConstructor = typeof AudioContext !== "undefined" ? AudioContext : browserWindow.webkitAudioContext;
  if (!AudioContextConstructor) return silentMetronome;

  const context = new AudioContextConstructor();
  const secondsPerBeat = 60 / bpm;
  let nextBeatAt = context.currentTime + 0.03;
  let beatIndex = 0;
  let stopped = false;

  const scheduleClick = (at: number, isDownbeat: boolean) => {
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    const duration = isDownbeat ? 0.07 : 0.045;

    oscillator.type = "square";
    oscillator.frequency.setValueAtTime(isDownbeat ? 1_320 : 880, at);
    gain.gain.setValueAtTime(0.0001, at);
    gain.gain.exponentialRampToValueAtTime(isDownbeat ? 0.18 : 0.1, at + 0.002);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + duration);
    oscillator.connect(gain);
    gain.connect(context.destination);
    oscillator.start(at);
    oscillator.stop(at + duration);
  };

  const schedule = () => {
    while (!stopped && nextBeatAt < context.currentTime + 0.12) {
      scheduleClick(nextBeatAt, beatIndex % 4 === 0);
      nextBeatAt += secondsPerBeat;
      beatIndex += 1;
    }
  };

  // The battle Start button is a user gesture; resume is required by browsers
  // that initially create an AudioContext in the suspended state.
  void context.resume().catch((error: unknown) => console.warn("Metronome could not start", error));
  schedule();
  const timer = setInterval(schedule, 25);

  return {
    stop: () => {
      if (stopped) return;
      stopped = true;
      clearInterval(timer);
      void context.close().catch((error: unknown) => console.warn("Metronome could not stop", error));
    },
  };
}
