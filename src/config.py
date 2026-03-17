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

# Difficulty modes — tolerance windows in milliseconds
DIFFICULTY_MODES = {
    "relaxed": {"perfect": 40, "good": 100, "ok": 180, "miss": 250},
    "strict":  {"perfect": 20, "good": 50,  "ok": 100, "miss": 150},
}
DEFAULT_DIFFICULTY = "relaxed"

# Active windows — set by set_difficulty()
PERFECT_WINDOW_MS = 40
GOOD_WINDOW_MS = 100
OK_WINDOW_MS = 180
MISS_WINDOW_MS = 250


def set_difficulty(mode: str):
    """Update the global tolerance windows."""
    global PERFECT_WINDOW_MS, GOOD_WINDOW_MS, OK_WINDOW_MS, MISS_WINDOW_MS
    windows = DIFFICULTY_MODES.get(mode, DIFFICULTY_MODES[DEFAULT_DIFFICULTY])
    PERFECT_WINDOW_MS = windows["perfect"]
    GOOD_WINDOW_MS = windows["good"]
    OK_WINDOW_MS = windows["ok"]
    MISS_WINDOW_MS = windows["miss"]


# Initialize to default
set_difficulty(DEFAULT_DIFFICULTY)

# Input
KEYBOARD_LAYER_KEYS = {
    "d": 0,
    "f": 0,
    "j": 1,
    "k": 1,
    "space": 2,
}

LAYER_KEY_LABELS = {
    0: "D/F",
    1: "J/K",
    2: "SPACE",
}

# Visual modes
VISUAL_MODES = ["orbits", "gameoflife", "automata", "boxing", "blacksmith", "dancebattle"]


# --- Preset system ---
# Each preset has a unique string ID, so reordering never breaks anything.

def _grouping_to_phases(groups: list[int]) -> list[float]:
    """Convert a grouping like [2,2,3] to normalized phases [0.0, 0.286, 0.571]."""
    total = sum(groups)
    phases = []
    pos = 0
    for g in groups:
        phases.append(pos / total)
        pos += g
    return phases


# Difficulty tiers
TIER_EASY = 1
TIER_MEDIUM = 2
TIER_HARD = 3
TIER_VERY_HARD = 4
TIER_EXPERT = 5

# Grade required to unlock next tier
TIER_UNLOCK_GRADES = {
    TIER_MEDIUM: "B",
    TIER_HARD: "B",
    TIER_VERY_HARD: "A",
    TIER_EXPERT: "A",
}


class Preset:
    """A single rhythm preset with all its metadata."""
    __slots__ = ("id", "name", "layers", "base_beats", "category", "tier")

    def __init__(self, id: str, name: str, layers: list, base_beats: int,
                 category: str, tier: int):
        self.id = id
        self.name = name
        self.layers = layers  # list of int (even) or list[float] (custom phases)
        self.base_beats = base_beats
        self.category = category
        self.tier = tier


# Master preset list — ordered by difficulty.
# The order here defines display order. IDs are stable identifiers.
PRESETS = [
    # --- Easy ---
    Preset("poly_3_2",      "3:2",               [3, 2], 2, "poly", TIER_EASY),
    Preset("poly_2_3",      "2:3",               [2, 3], 4, "poly", TIER_EASY),
    Preset("odd_5_4_3p2",   "5/4 (3+2)",         [_grouping_to_phases([3, 2])], 4, "odd", TIER_EASY),
    Preset("odd_5_4_2p3",   "5/4 (2+3)",         [_grouping_to_phases([2, 3])], 4, "odd", TIER_EASY),

    # --- Medium ---
    Preset("poly_3_4",      "3:4",               [3, 4], 4, "poly", TIER_MEDIUM),
    Preset("poly_4_3",      "4:3",               [4, 3], 4, "poly", TIER_MEDIUM),
    Preset("world_bossa",   "Bossa Nova",        [_grouping_to_phases([3, 3, 4, 3, 3])], 4, "world", TIER_MEDIUM),
    Preset("world_afro6",   "Afro-Cuban 6/8",    [_grouping_to_phases([2, 1, 2, 1])], 8, "world", TIER_MEDIUM),
    Preset("world_afro12",  "Afro-Cuban 12/8 Bell", [_grouping_to_phases([2, 2, 1, 2, 2, 2, 1])], 8, "world", TIER_MEDIUM),
    Preset("odd_7_8_223",   "7/8 (2+2+3)",       [_grouping_to_phases([2, 2, 3])], 8, "odd", TIER_MEDIUM),
    Preset("odd_7_8_322",   "7/8 (3+2+2)",       [_grouping_to_phases([3, 2, 2])], 8, "odd", TIER_MEDIUM),
    Preset("odd_7_8_232",   "7/8 (2+3+2)",       [_grouping_to_phases([2, 3, 2])], 8, "odd", TIER_MEDIUM),
    Preset("world_rumba",   "Rumba Clave",       [_grouping_to_phases([3, 3, 4, 2, 4])], 4, "world", TIER_MEDIUM),
    Preset("world_son",     "Son Clave",         [_grouping_to_phases([3, 3, 4, 2, 4])], 4, "world", TIER_MEDIUM),

    # --- Hard ---
    Preset("poly_5_4",      "5:4",               [5, 4], 4, "poly", TIER_HARD),
    Preset("poly_5_3",      "5:3",               [5, 3], 4, "poly", TIER_HARD),
    Preset("odd_9_8_2223",  "9/8 (2+2+2+3)",     [_grouping_to_phases([2, 2, 2, 3])], 8, "odd", TIER_HARD),
    Preset("odd_9_8_333",   "9/8 (3+3+3)",       [_grouping_to_phases([3, 3, 3])], 8, "odd", TIER_HARD),
    Preset("pg_5_4v4",      "5/4 (3+2) vs 4",    [_grouping_to_phases([3, 2]), 4], 4, "poly-grouped", TIER_HARD),
    Preset("pg_7_8v3",      "7/8 (2+2+3) vs 3",  [_grouping_to_phases([2, 2, 3]), 3], 8, "poly-grouped", TIER_HARD),
    Preset("world_taksim",  "Taksim 10/8",       [_grouping_to_phases([3, 2, 2, 3])], 8, "world", TIER_HARD),

    # --- Very Hard ---
    Preset("poly_7_4",      "7:4",               [7, 4], 4, "poly", TIER_VERY_HARD),
    Preset("poly_7_8",      "7:8",               [7, 8], 8, "poly", TIER_VERY_HARD),
    Preset("pg_7_8v4",      "7/8 (3+2+2) vs 4",  [_grouping_to_phases([3, 2, 2]), 4], 8, "poly-grouped", TIER_VERY_HARD),
    Preset("pg_9_8v4",      "9/8 (2+2+2+3) vs 4",[_grouping_to_phases([2, 2, 2, 3]), 4], 8, "poly-grouped", TIER_VERY_HARD),
    Preset("odd_11_8",      "11/8 (3+3+3+2)",    [_grouping_to_phases([3, 3, 3, 2])], 8, "odd", TIER_VERY_HARD),
    Preset("odd_13_8",      "13/8 (3+3+2+3+2)",  [_grouping_to_phases([3, 3, 2, 3, 2])], 8, "odd", TIER_VERY_HARD),

    # --- Expert ---
    Preset("adv_5_4_3",     "5:4:3",             [5, 4, 3], 4, "advanced", TIER_EXPERT),
    Preset("adv_3_4_5",     "3:4:5",             [3, 4, 5], 4, "advanced", TIER_EXPERT),
    Preset("adv_7_5_3",     "7:5:3",             [7, 5, 3], 4, "advanced", TIER_EXPERT),
]

# Lookup helpers — derived from PRESETS, never hardcoded
PRESET_BY_ID: dict[str, Preset] = {p.id: p for p in PRESETS}
PRESET_INDEX_BY_ID: dict[str, int] = {p.id: i for i, p in enumerate(PRESETS)}
DEFAULT_PRESET_ID = "poly_3_2"

# Surprise Me pool — all indices (auto-generated)
SURPRISE_POOL = list(range(len(PRESETS)))
