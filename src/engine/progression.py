"""Progressive difficulty — tier-based preset unlocking.

Uses preset IDs (not indices) for stability. Tiers are derived from
the tier field on each Preset object in config.PRESETS.
"""

import json
import os
from src.config import (
    PRESETS, PRESET_INDEX_BY_ID,
    TIER_EASY, TIER_MEDIUM, TIER_HARD, TIER_VERY_HARD, TIER_EXPERT,
    TIER_UNLOCK_GRADES,
)

PROGRESS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "progress.json")

GRADE_ORDER = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}

# Derive tier membership from preset metadata — no hardcoded index lists
TIER_NUMBERS = sorted({p.tier for p in PRESETS})

# Map tier -> list of preset IDs in that tier
TIER_PRESET_IDS: dict[int, list[str]] = {}
for _p in PRESETS:
    TIER_PRESET_IDS.setdefault(_p.tier, []).append(_p.id)

# Map tier -> list of preset indices (for progression UI)
TIER_PRESET_INDICES: dict[int, list[int]] = {}
for _tier, _ids in TIER_PRESET_IDS.items():
    TIER_PRESET_INDICES[_tier] = [PRESET_INDEX_BY_ID[_id] for _id in _ids]


def _load_progress() -> dict:
    try:
        with open(PROGRESS_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"unlocked_tiers": [TIER_EASY], "best_grades": {}}


def _save_progress(data: dict):
    os.makedirs(os.path.dirname(PROGRESS_PATH), exist_ok=True)
    with open(PROGRESS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def get_unlocked_tiers() -> list[int]:
    return _load_progress().get("unlocked_tiers", [TIER_EASY])


def get_unlocked_preset_indices() -> set[int]:
    """Return set of preset indices that are unlocked."""
    unlocked_tiers = set(get_unlocked_tiers())
    indices = set()
    for tier, idx_list in TIER_PRESET_INDICES.items():
        if tier in unlocked_tiers:
            indices.update(idx_list)
    return indices


def is_preset_unlocked(preset_idx: int) -> bool:
    return preset_idx in get_unlocked_preset_indices()


def get_preset_tier(preset_idx: int) -> int | None:
    """Which tier does a preset belong to?"""
    if 0 <= preset_idx < len(PRESETS):
        return PRESETS[preset_idx].tier
    return None


def record_grade(preset_id: str, grade: str) -> list[int]:
    """Record a grade for a preset (by ID). Returns list of newly unlocked tier numbers."""
    progress = _load_progress()
    grades = progress.get("best_grades", {})

    # Update best grade (keyed by preset ID, not index)
    old_grade = grades.get(preset_id, "")
    if GRADE_ORDER.get(grade, 0) > GRADE_ORDER.get(old_grade, 0):
        grades[preset_id] = grade

    progress["best_grades"] = grades

    # Check unlocks
    newly_unlocked = []
    unlocked = set(progress.get("unlocked_tiers", [TIER_EASY]))

    for tier_num in TIER_NUMBERS:
        if tier_num in unlocked:
            continue
        req_grade = TIER_UNLOCK_GRADES.get(tier_num)
        if req_grade is None:
            continue

        # Need the required grade on any preset from the previous tier
        prev_tier = tier_num - 1
        prev_ids = TIER_PRESET_IDS.get(prev_tier, [])

        for pid in prev_ids:
            best = grades.get(pid, "")
            if GRADE_ORDER.get(best, 0) >= GRADE_ORDER.get(req_grade, 0):
                unlocked.add(tier_num)
                newly_unlocked.append(tier_num)
                break

    progress["unlocked_tiers"] = sorted(unlocked)
    _save_progress(progress)
    return newly_unlocked
