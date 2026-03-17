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
VISUAL_MODES = ["orbits", "gameoflife", "automata", "boxing", "blacksmith", "dancebattle"]

# Polyrhythm presets
# Each entry: (name, layers, base_beats, category)
# layers: list of int (evenly spaced) or list of floats (custom beat phases 0.0-1.0)
#
# Helper: convert grouping like [2,2,3] in 7/8 to phases
def _grouping_to_phases(groups: list[int]) -> list[float]:
    """Convert a grouping like [2,2,3] to normalized phases [0.0, 0.286, 0.571]."""
    total = sum(groups)
    phases = []
    pos = 0
    for g in groups:
        phases.append(pos / total)
        pos += g
    return phases

PRESETS = [
    # --- Easy: simple polyrhythms ---
    ("3:2", [3, 2], 2, "poly"),                                             # 0
    ("2:3", [2, 3], 4, "poly"),                                             # 1
    ("5/4 (3+2)", [_grouping_to_phases([3, 2])], 4, "odd"),                 # 2
    ("5/4 (2+3)", [_grouping_to_phases([2, 3])], 4, "odd"),                 # 3

    # --- Medium: classic polys + world rhythms ---
    ("3:4", [3, 4], 4, "poly"),                                             # 4
    ("4:3", [4, 3], 4, "poly"),                                             # 5
    ("Bossa Nova", [_grouping_to_phases([3, 3, 4, 3, 3])], 4, "world"),     # 6
    ("Afro-Cuban 6/8", [_grouping_to_phases([2, 1, 2, 1])], 8, "world"),    # 7
    ("Afro-Cuban 12/8 Bell", [_grouping_to_phases([2, 2, 1, 2, 2, 2, 1])], 8, "world"),  # 8
    ("7/8 (2+2+3)", [_grouping_to_phases([2, 2, 3])], 8, "odd"),            # 8
    ("7/8 (3+2+2)", [_grouping_to_phases([3, 2, 2])], 8, "odd"),            # 9
    ("7/8 (2+3+2)", [_grouping_to_phases([2, 3, 2])], 8, "odd"),            # 10
    ("Rumba Clave", [_grouping_to_phases([3, 3, 4, 2, 4])], 4, "world"),    # 11
    ("Son Clave", [_grouping_to_phases([3, 3, 4, 2, 4])], 4, "world"),      # 12

    # --- Hard: wider polys + grouped polys ---
    ("5:4", [5, 4], 4, "poly"),                                             # 13
    ("5:3", [5, 3], 4, "poly"),                                             # 14
    ("9/8 (2+2+2+3)", [_grouping_to_phases([2, 2, 2, 3])], 8, "odd"),       # 15
    ("9/8 (3+3+3)", [_grouping_to_phases([3, 3, 3])], 8, "odd"),            # 16
    ("5/4 (3+2) vs 4", [_grouping_to_phases([3, 2]), 4], 4, "poly-grouped"),# 17
    ("7/8 (2+2+3) vs 3", [_grouping_to_phases([2, 2, 3]), 3], 8, "poly-grouped"),  # 18
    ("Taksim 10/8", [_grouping_to_phases([3, 2, 2, 3])], 8, "world"),       # 19

    # --- Very Hard: big ratios + complex meters ---
    ("7:4", [7, 4], 4, "poly"),                                             # 20
    ("7:8", [7, 8], 8, "poly"),                                             # 21
    ("7/8 (3+2+2) vs 4", [_grouping_to_phases([3, 2, 2]), 4], 8, "poly-grouped"),  # 22
    ("9/8 (2+2+2+3) vs 4", [_grouping_to_phases([2, 2, 2, 3]), 4], 8, "poly-grouped"),  # 23
    ("11/8 (3+3+3+2)", [_grouping_to_phases([3, 3, 3, 2])], 8, "odd"),      # 24
    ("13/8 (3+3+2+3+2)", [_grouping_to_phases([3, 3, 2, 3, 2])], 8, "odd"), # 25

    # --- Expert: 3 simultaneous layers ---
    ("5:4:3", [5, 4, 3], 4, "advanced"),                                    # 26
    ("3:4:5", [3, 4, 5], 4, "advanced"),                                    # 27
    ("7:5:3", [7, 5, 3], 4, "advanced"),                                    # 28
]

# Surprise Me pool — all indices
SURPRISE_POOL = list(range(len(PRESETS)))
