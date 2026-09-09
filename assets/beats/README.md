# Beat assets

Place licensed `.mp3`, `.m4a`, or `.wav` beats in this directory.  The MVP's
metadata lives in `src/features/battle/beats.ts`; set each `audioUri` to a
bundled Expo asset or a future imported local file URI when real files are available.

Until then the Battle screen keeps precise BPM timing with its visual four-beat count.
