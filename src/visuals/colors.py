"""Neon/synthwave color palette."""

# Background
BG_DARK = (8, 8, 24)
BG_PURPLE = (16, 8, 32)

# Neon primaries
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
PURPLE = (157, 0, 255)
HOT_PINK = (255, 16, 128)
ELECTRIC_BLUE = (0, 128, 255)
NEON_GREEN = (0, 255, 128)
ORANGE = (255, 128, 0)
YELLOW = (255, 255, 0)

# Rating colors
COLOR_PERFECT = CYAN
COLOR_GOOD = NEON_GREEN
COLOR_OK = YELLOW
COLOR_MISS = HOT_PINK

# Layer colors (for multi-layer polyrhythms)
LAYER_COLORS = [
    CYAN,
    MAGENTA,
    NEON_GREEN,
    ORANGE,
    ELECTRIC_BLUE,
    PURPLE,
    HOT_PINK,
    YELLOW,
]

# UI
TEXT_COLOR = (200, 200, 220)
TEXT_DIM = (100, 100, 130)
HUD_BG = (8, 8, 24, 160)  # Semi-transparent

# Glow intensities
GLOW_ALPHA = 80
BLOOM_SCALE = 4  # Downscale factor for bloom effect

# Grid
GRID_COLOR = (40, 20, 60)
GRID_BRIGHT = (80, 40, 120)
