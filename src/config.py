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
VISUAL_MODES = ["orbits", "gameoflife", "automata", "boxing", "blacksmith", "dancebattle", "cashier", "samurai"]


# --- Preset system ---
# Each preset has a unique string ID, so reordering never breaks anything.

def _grouping(groups: list[int]) -> dict:
    """Convert a grouping like [2,2,3] to all subdivisions with accent markers.

    Returns dict with:
      phases: all subdivision positions (e.g. 7 positions for [2,2,3])
      accents: which beats are grouping starts (accented)

    Example: [2,2,3] in 7/8 ->
      phases:  [0/7, 1/7, 2/7, 3/7, 4/7, 5/7, 6/7]
      accents: [True, False, True, False, True, False, False]
                ^           ^           ^
                group 1     group 2     group 3
    """
    total = sum(groups)
    phases = [i / total for i in range(total)]

    # Mark group starts as accents
    accents = [False] * total
    pos = 0
    for g in groups:
        accents[pos] = True
        pos += g

    return {"phases": phases, "accents": accents}


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
        self.layers = layers  # list of: int (even), dict (grouped), or list[float] (legacy)
        self.base_beats = base_beats
        self.category = category
        self.tier = tier


# Section names for preset grouping
SECTION_POLYRHYTHMS = "Polyrhythms"
SECTION_TIME_SIGNATURES = "Time Signatures"

# Master preset list — ordered by section, then difficulty.
# The order here defines display order. IDs are stable identifiers.
PRESETS = [
    # ===== POLYRHYTHMS =====
    # --- Easy ---
    Preset("poly_3_2",      "3:2",               [3, 2], 2, "poly", TIER_EASY),
    Preset("poly_2_3",      "2:3",               [2, 3], 4, "poly", TIER_EASY),

    # --- Medium ---
    Preset("poly_3_4",      "3:4",               [3, 4], 4, "poly", TIER_MEDIUM),
    Preset("poly_4_3",      "4:3",               [4, 3], 4, "poly", TIER_MEDIUM),

    # --- Hard ---
    Preset("poly_5_4",      "5:4",               [5, 4], 4, "poly", TIER_HARD),
    Preset("poly_5_3",      "5:3",               [5, 3], 4, "poly", TIER_HARD),
    Preset("pg_5_4v4",      "5/4 (3+2) vs 4",    [_grouping([3, 2]), 4], 4, "poly-grouped", TIER_HARD),
    Preset("pg_7_8v3",      "7/8 (2+2+3) vs 3",  [_grouping([2, 2, 3]), 3], 8, "poly-grouped", TIER_HARD),

    # --- Very Hard ---
    Preset("poly_7_4",      "7:4",               [7, 4], 4, "poly", TIER_VERY_HARD),
    Preset("poly_7_8",      "7:8",               [7, 8], 8, "poly", TIER_VERY_HARD),
    Preset("pg_7_8v4",      "7/8 (3+2+2) vs 4",  [_grouping([3, 2, 2]), 4], 8, "poly-grouped", TIER_VERY_HARD),
    Preset("pg_9_8v4",      "9/8 (2+2+2+3) vs 4",[_grouping([2, 2, 2, 3]), 4], 8, "poly-grouped", TIER_VERY_HARD),

    # --- Expert ---
    Preset("adv_5_4_3",     "5:4:3",             [5, 4, 3], 4, "advanced", TIER_EXPERT),
    Preset("adv_3_4_5",     "3:4:5",             [3, 4, 5], 4, "advanced", TIER_EXPERT),
    Preset("adv_7_5_3",     "7:5:3",             [7, 5, 3], 4, "advanced", TIER_EXPERT),

    # ===== TIME SIGNATURES =====
    # --- Easy ---
    Preset("odd_5_4_3p2",   "5/4 (3+2)",         [_grouping([3, 2])], 4, "odd", TIER_EASY),
    Preset("odd_5_4_2p3",   "5/4 (2+3)",         [_grouping([2, 3])], 4, "odd", TIER_EASY),

    # --- Medium ---
    Preset("odd_7_8_223",   "7/8 (2+2+3)",       [_grouping([2, 2, 3])], 8, "odd", TIER_MEDIUM),
    Preset("odd_7_8_322",   "7/8 (3+2+2)",       [_grouping([3, 2, 2])], 8, "odd", TIER_MEDIUM),
    Preset("odd_7_8_232",   "7/8 (2+3+2)",       [_grouping([2, 3, 2])], 8, "odd", TIER_MEDIUM),
    Preset("world_bossa",   "Bossa Nova",        [_grouping([3, 3, 4, 3, 3])], 4, "world", TIER_MEDIUM),
    Preset("world_afro6",   "Afro-Cuban 6/8",    [_grouping([2, 1, 2, 1])], 8, "world", TIER_MEDIUM),
    Preset("world_afro12",  "Afro-Cuban 12/8 Bell", [_grouping([2, 2, 1, 2, 2, 2, 1])], 8, "world", TIER_MEDIUM),
    Preset("world_rumba",   "Rumba Clave",       [_grouping([3, 3, 4, 2, 4])], 4, "world", TIER_MEDIUM),
    Preset("world_son",     "Son Clave",         [_grouping([3, 3, 4, 2, 4])], 4, "world", TIER_MEDIUM),

    # --- Hard ---
    Preset("odd_9_8_2223",  "9/8 (2+2+2+3)",     [_grouping([2, 2, 2, 3])], 8, "odd", TIER_HARD),
    Preset("odd_9_8_333",   "9/8 (3+3+3)",       [_grouping([3, 3, 3])], 8, "odd", TIER_HARD),
    Preset("world_taksim",  "Taksim 10/8",       [_grouping([3, 2, 2, 3])], 8, "world", TIER_HARD),

    # --- Very Hard ---
    Preset("odd_11_8",      "11/8 (3+3+3+2)",    [_grouping([3, 3, 3, 2])], 8, "odd", TIER_VERY_HARD),
    Preset("odd_13_8",      "13/8 (3+3+2+3+2)",  [_grouping([3, 3, 2, 3, 2])], 8, "odd", TIER_VERY_HARD),
]

# Categories that belong to each section
_POLY_CATEGORIES = {"poly", "poly-grouped", "advanced"}
_TIMESIG_CATEGORIES = {"odd", "world"}

def get_preset_section(preset: Preset) -> str:
    """Return the section name for a preset."""
    if preset.category in _POLY_CATEGORIES:
        return SECTION_POLYRHYTHMS
    return SECTION_TIME_SIGNATURES

# Index of first preset in each section (for rendering headers)
SECTION_BREAKS: list[tuple[int, str]] = []
_prev_section = ""
for _i, _p in enumerate(PRESETS):
    _sec = get_preset_section(_p)
    if _sec != _prev_section:
        SECTION_BREAKS.append((_i, _sec))
        _prev_section = _sec

# Section index ranges: list of (start, end, name) — end is exclusive
SECTION_RANGES: list[tuple[int, int, str]] = []
for _idx in range(len(SECTION_BREAKS)):
    _start, _name = SECTION_BREAKS[_idx]
    _end = SECTION_BREAKS[_idx + 1][0] if _idx + 1 < len(SECTION_BREAKS) else len(PRESETS)
    SECTION_RANGES.append((_start, _end, _name))

def get_section_for_index(idx: int) -> int:
    """Return the section number (index into SECTION_RANGES) for a preset index."""
    for si, (start, end, _) in enumerate(SECTION_RANGES):
        if start <= idx < end:
            return si
    return 0

# Lookup helpers — derived from PRESETS, never hardcoded
PRESET_BY_ID: dict[str, Preset] = {p.id: p for p in PRESETS}
PRESET_INDEX_BY_ID: dict[str, int] = {p.id: i for i, p in enumerate(PRESETS)}
DEFAULT_PRESET_ID = "poly_3_2"

# Surprise Me pool — all indices (auto-generated)
SURPRISE_POOL = list(range(len(PRESETS)))
