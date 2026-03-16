"""Global configuration and presets for the polyrhythm trainer."""

# Display
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
WINDOW_TITLE = "Polyrhythm Trainer"

# Audio
SAMPLE_RATE = 44100
AUDIO_BUFFER = 512  # Low latency
AUDIO_CHANNELS = 2
METRONOME_VOLUME = 0.7
LATENCY_COMPENSATION_MS = 20.0  # Adjust per system

# Timing / Scoring
DEFAULT_BPM = 120
MIN_BPM = 40
MAX_BPM = 300

# Tolerance windows in milliseconds
PERFECT_WINDOW_MS = 20
GOOD_WINDOW_MS = 50
OK_WINDOW_MS = 100
MISS_WINDOW_MS = 150  # Beyond this, not registered as attempt

# Input
KEYBOARD_LAYER_KEYS = {
    "d": 0,       # Layer 0 — left hand
    "f": 0,       # Layer 0 — left hand (either finger)
    "j": 1,       # Layer 1 — right hand
    "k": 1,       # Layer 1 — right hand (either finger)
    "space": 2,   # Layer 2 — either hand (for 3-layer presets)
}

# Short labels shown next to each layer in visuals
LAYER_KEY_LABELS = {
    0: "D/F",
    1: "J/K",
    2: "SPACE",
}

# Visual modes
VISUAL_MODES = ["orbits", "gameoflife", "automata", "boxing", "blacksmith"]

# Polyrhythm presets: (name, layers as list of beat counts, base_beats)
# e.g. ("3:4", [3, 4], 4) means 3 against 4, with 4 as the base
PRESETS = [
    ("Simple 4/4", [4], 4),
    ("3/4 Waltz", [3], 4),
    ("5/4", [5], 4),
    ("7/8", [7], 8),
    ("3:2", [3, 2], 2),
    ("3:4", [3, 4], 4),
    ("4:3", [4, 3], 4),
    ("5:4", [5, 4], 4),
    ("5:3", [5, 3], 4),
    ("7:4", [7, 4], 4),
    ("7:8", [7, 8], 8),
    ("5:4:3", [5, 4, 3], 4),
]
