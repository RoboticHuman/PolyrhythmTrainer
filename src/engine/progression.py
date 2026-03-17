"""Progressive difficulty — tier-based preset unlocking."""

import json
import os

PROGRESS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "progress.json")

# Tier definitions — ordered by difficulty
TIERS = [
    {"tier": 1, "presets": [0, 1, 2, 3],                          "require_grade": None, "require_tier": None},
    {"tier": 2, "presets": [4, 5, 6, 7, 8, 9, 10, 11, 12, 13],   "require_grade": "B",  "require_tier": 1},
    {"tier": 3, "presets": [14, 15, 16, 17, 18, 19, 20],          "require_grade": "B",  "require_tier": 2},
    {"tier": 4, "presets": [21, 22, 23, 24, 25, 26],              "require_grade": "A",  "require_tier": 3},
    {"tier": 5, "presets": [27, 28, 29],                           "require_grade": "A",  "require_tier": 4},
]

GRADE_ORDER = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}

# Build lookup: tier_num -> preset indices
TIER_PRESETS = {t["tier"]: t["presets"] for t in TIERS}


def _load_progress() -> dict:
    try:
        with open(PROGRESS_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"unlocked_tiers": [1], "best_grades": {}}


def _save_progress(data: dict):
    os.makedirs(os.path.dirname(PROGRESS_PATH), exist_ok=True)
    with open(PROGRESS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def get_unlocked_tiers() -> list[int]:
    return _load_progress().get("unlocked_tiers", [1])


def get_unlocked_preset_indices() -> set[int]:
    unlocked_tiers = set(get_unlocked_tiers())
    indices = set()
    for tier in TIERS:
        if tier["tier"] in unlocked_tiers:
            indices.update(tier["presets"])
    return indices


def is_preset_unlocked(preset_idx: int) -> bool:
    return preset_idx in get_unlocked_preset_indices()


def get_preset_tier(preset_idx: int) -> int | None:
    for tier in TIERS:
        if preset_idx in tier["presets"]:
            return tier["tier"]
    return None


def record_grade(preset_idx: int, grade: str) -> list[int]:
    progress = _load_progress()
    grades = progress.get("best_grades", {})
    key = str(preset_idx)

    old_grade = grades.get(key, "")
    if GRADE_ORDER.get(grade, 0) > GRADE_ORDER.get(old_grade, 0):
        grades[key] = grade

    progress["best_grades"] = grades

    newly_unlocked = []
    unlocked = set(progress.get("unlocked_tiers", [1]))

    for tier_def in TIERS:
        tier_num = tier_def["tier"]
        if tier_num in unlocked:
            continue
        req_grade = tier_def["require_grade"]
        req_tier = tier_def["require_tier"]
        if req_tier is None:
            continue

        req_tier_presets = TIER_PRESETS.get(req_tier, [])
        for pidx in req_tier_presets:
            best = grades.get(str(pidx), "")
            if GRADE_ORDER.get(best, 0) >= GRADE_ORDER.get(req_grade, 0):
                unlocked.add(tier_num)
                newly_unlocked.append(tier_num)
                break

    progress["unlocked_tiers"] = sorted(unlocked)
    _save_progress(progress)
    return newly_unlocked
