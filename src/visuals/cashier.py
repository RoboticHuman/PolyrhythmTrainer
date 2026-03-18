"""Cashier visualizer.

A bored cashier scanning items on a conveyor belt to the rhythm.
Good hits make them excited and fast. Misses make them grumpy.
Zoomed-in view — counter fills lower half, characters are large and detailed.
"""

import math
import random
import time
import pygame
from src.visuals.base import BaseVisualizer
from src.visuals.colors import (
    BG_DARK, LAYER_COLORS, CYAN, MAGENTA, NEON_GREEN, HOT_PINK,
    YELLOW, ORANGE, rating_color
)
from src.visuals.effects import bloom_pass, ParticleSystem
from src.visuals.timeline import Timeline
from src.visuals.speechbubble import SpeechBubbleState
from src.engine.scoring import HitRating


# Scene colors
COUNTER_FRONT = (55, 45, 40)
COUNTER_TOP = (75, 65, 55)
CONVEYOR_COLOR = (50, 50, 55)
CONVEYOR_BELT = (35, 35, 40)
FLOOR_COLOR = (22, 18, 28)
WALL_COLOR = (30, 25, 35)

# Item colors
ITEM_COLORS = [
    (200, 60, 60), (60, 160, 60), (60, 60, 200), (200, 200, 60),
    (200, 120, 60), (160, 60, 200), (60, 200, 200),
]
ITEM_SHAPES = ["box", "tall", "round", "small"]

# Speech pools
MOOD_BORED = ["Ugh...", "So slow...", "*yawn*", "Break when?", "Is it 5 yet?", "Zzzz..."]
MOOD_HAPPY = ["Beep!", "Got it!", "Nice!", "On a roll!", "Speed scan!", "Next!"]
MOOD_EXCITED = ["I'M ON FIRE!", "UNSTOPPABLE!", "FASTEST SCANNER!", "NEW RECORD!", "LETS GOOO!"]
MOOD_GRUMPY = ["Ugh, really?", "Come ON!", "*sigh*", "This job...", "Not again!"]
CUSTOMER_IMPATIENT = ["Hurry up!", "I'm late!", "Come on...", "Seriously?!", "My ice cream!", "*taps foot*"]
CUSTOMER_HAPPY = ["Wow, fast!", "Nice job!", "Thanks!", "Impressive!", "Great service!"]


class Item:
    """A grocery item on the conveyor belt."""

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.color = random.choice(ITEM_COLORS)
        self.shape = random.choice(ITEM_SHAPES)
        self.scanned = False
        self.scan_time = 0.0
        self.width = random.randint(22, 38)
        self.height = {"box": 26, "tall": 40, "round": 24, "small": 18}[self.shape]

    def draw(self, surface: pygame.Surface):
        x, y = int(self.x), int(self.y)
        w, h = self.width, self.height

        color = self.color
        if self.scanned:
            age = time.perf_counter() - self.scan_time
            if age < 0.2:
                flash = 1.0 - age / 0.2
                color = tuple(min(255, int(c + flash * 120)) for c in self.color)

        if self.shape == "box":
            pygame.draw.rect(surface, color, (x - w // 2, y - h, w, h), border_radius=4)
            # Label
            pygame.draw.rect(surface, tuple(max(0, c - 40) for c in color),
                             (x - w // 3, y - h * 2 // 3, w * 2 // 3, h // 3), border_radius=2)
        elif self.shape == "tall":
            pygame.draw.rect(surface, color, (x - w // 3, y - h, w * 2 // 3, h), border_radius=5)
            # Cap
            pygame.draw.rect(surface, tuple(min(255, c + 30) for c in color),
                             (x - w // 4, y - h, w // 2, 8), border_radius=3)
        elif self.shape == "round":
            pygame.draw.ellipse(surface, color, (x - w // 2, y - h, w, h))
            # Shine
            pygame.draw.arc(surface, tuple(min(255, c + 50) for c in color),
                            (x - w // 3, y - h + 3, w // 2, h // 2), 0.5, 2.0, 2)
        elif self.shape == "small":
            pygame.draw.rect(surface, color, (x - w // 2, y - h, w, h), border_radius=3)

        # Shadow underneath
        pygame.draw.ellipse(surface, (20, 18, 25),
                            (x - w // 2 - 2, y - 2, w + 4, 5))


class Cashier:
    """Large, detailed cashier character."""

    def __init__(self, x: float, y: float):
        self.base_x = x
        self.base_y = y
        self.mood = "bored"
        self.scan_time = 0.0

    def trigger_scan(self):
        self.scan_time = time.perf_counter()

    def draw(self, surface: pygame.Surface, beat_phase: float):
        cx = int(self.base_x)
        cy = int(self.base_y)

        scan_age = time.perf_counter() - self.scan_time
        scan_t = math.sin((scan_age / 0.25) * math.pi) if scan_age < 0.25 else 0.0

        # Mood-based movement
        bob = math.sin(beat_phase * math.pi * 2)
        if self.mood == "bored":
            bob *= 2
            cy += 6  # Slouch
        elif self.mood == "excited":
            bob *= 5
        elif self.mood == "grumpy":
            bob *= 1.5
            cy += 3
        else:
            bob *= 3
        cy += int(bob)

        # Shirt color by mood
        shirt = {
            "bored": (70, 70, 90),
            "happy": (50, 110, 70),
            "excited": (70, 50, 150),
            "grumpy": (110, 55, 55),
        }.get(self.mood, (70, 70, 90))

        skin = (200, 165, 130)
        hair = (50, 35, 25)

        head_r = 22
        body_w = 38
        body_h = 55
        shoulder_w = body_w + 12

        # --- Torso ---
        pygame.draw.rect(surface, shirt,
                         (cx - body_w // 2, cy, body_w, body_h),
                         border_radius=8)
        # Shoulders
        pygame.draw.rect(surface, shirt,
                         (cx - shoulder_w // 2, cy, shoulder_w, 18),
                         border_radius=8)

        # Vest/apron
        vest = tuple(max(0, c - 25) for c in shirt)
        pygame.draw.rect(surface, vest,
                         (cx - body_w // 2 + 5, cy + 12, body_w - 10, body_h - 18),
                         border_radius=4)

        # Name tag
        pygame.draw.rect(surface, (220, 220, 200),
                         (cx + 4, cy + 5, 16, 9), border_radius=2)
        pygame.draw.rect(surface, (180, 180, 160),
                         (cx + 6, cy + 7, 12, 5), border_radius=1)

        # --- Arms ---
        shoulder_y = cy + 10

        # Left arm
        la_x = cx - shoulder_w // 2 - 3
        if self.mood == "excited":
            wave = math.sin(time.perf_counter() * 10) * 15
            la_end = (la_x - 10, shoulder_y - 25 + int(wave))
        elif self.mood == "grumpy":
            la_end = (la_x - 5, shoulder_y + 25)  # Hanging limp
        else:
            la_end = (la_x - 8, shoulder_y + 20)
        pygame.draw.line(surface, skin, (la_x, shoulder_y), la_end, 7)
        pygame.draw.circle(surface, skin, la_end, 7)

        # Right arm (scanning)
        ra_x = cx + shoulder_w // 2 + 3
        ra_end_x = ra_x + int(scan_t * 35)
        ra_end_y = shoulder_y + 15 - int(scan_t * 20)
        pygame.draw.line(surface, skin, (ra_x, shoulder_y),
                         (ra_end_x, ra_end_y), 7)
        pygame.draw.circle(surface, skin, (ra_end_x, ra_end_y), 7)

        # Scanner
        scanner_glow = scan_t > 0.3
        sc_color = (220, 40, 40) if scanner_glow else (90, 90, 100)
        pygame.draw.rect(surface, sc_color,
                         (ra_end_x - 3, ra_end_y - 14, 12, 10), border_radius=3)
        if scanner_glow:
            pygame.draw.line(surface, (255, 80, 80),
                             (ra_end_x + 3, ra_end_y - 14),
                             (ra_end_x + 3, ra_end_y - 4), 2)

        # --- Head ---
        head_y = cy - head_r + 5
        pygame.draw.circle(surface, skin, (cx, head_y), head_r)

        # Hair
        pygame.draw.arc(surface, hair,
                        (cx - head_r - 1, head_y - head_r - 1,
                         head_r * 2 + 2, head_r * 2 + 2),
                        0.3, 2.8, 6)

        # Ears
        pygame.draw.circle(surface, skin, (cx - head_r + 2, head_y + 2), 5)
        pygame.draw.circle(surface, skin, (cx + head_r - 2, head_y + 2), 5)

        # --- Face ---
        eye_y = head_y - 3
        mouth_y = head_y + 9

        if self.mood == "bored":
            # Droopy half-closed eyes
            pygame.draw.line(surface, (35, 25, 20), (cx - 8, eye_y), (cx - 3, eye_y + 1), 3)
            pygame.draw.line(surface, (35, 25, 20), (cx + 3, eye_y + 1), (cx + 8, eye_y), 3)
            # Flat mouth
            pygame.draw.line(surface, (35, 25, 20), (cx - 6, mouth_y), (cx + 6, mouth_y), 2)
        elif self.mood == "happy":
            # Bright eyes
            pygame.draw.circle(surface, (35, 25, 20), (cx - 6, eye_y), 3)
            pygame.draw.circle(surface, (35, 25, 20), (cx + 6, eye_y), 3)
            # Smile
            pygame.draw.arc(surface, (35, 25, 20),
                            (cx - 8, mouth_y - 4, 16, 12), 3.5, 5.9, 2)
        elif self.mood == "excited":
            # Big sparkly eyes
            for ex in (cx - 7, cx + 7):
                pygame.draw.circle(surface, (35, 25, 20), (ex, eye_y), 4)
                pygame.draw.circle(surface, (255, 255, 255), (ex - 1, eye_y - 1), 2)
            # Big open grin
            pygame.draw.arc(surface, (35, 25, 20),
                            (cx - 10, mouth_y - 6, 20, 16), 3.3, 6.0, 3)
            # Blush
            pygame.draw.circle(surface, (230, 150, 130), (cx - 14, mouth_y - 2), 5)
            pygame.draw.circle(surface, (230, 150, 130), (cx + 14, mouth_y - 2), 5)
        elif self.mood == "grumpy":
            # Angry brows
            pygame.draw.line(surface, (35, 25, 20),
                             (cx - 10, eye_y - 5), (cx - 3, eye_y - 2), 3)
            pygame.draw.line(surface, (35, 25, 20),
                             (cx + 10, eye_y - 5), (cx + 3, eye_y - 2), 3)
            pygame.draw.circle(surface, (35, 25, 20), (cx - 6, eye_y + 1), 3)
            pygame.draw.circle(surface, (35, 25, 20), (cx + 6, eye_y + 1), 3)
            # Frown
            pygame.draw.arc(surface, (35, 25, 20),
                            (cx - 7, mouth_y + 2, 14, 10), 0.3, 2.8, 2)


class WaitingCustomer:
    """A large, detailed customer waiting in line."""

    def __init__(self, x: float, y: float, idx: int):
        self.x = x
        self.y = y
        # Distinct per customer
        rng = random.Random(idx * 77 + 13)
        self.shirt = (rng.randint(50, 130), rng.randint(40, 110), rng.randint(60, 140))
        self.skin = (rng.randint(160, 220), rng.randint(130, 185), rng.randint(100, 155))
        self.hair = (rng.randint(30, 80), rng.randint(20, 50), rng.randint(15, 40))
        self.height_scale = rng.uniform(0.85, 1.1)
        self.phase_offset = rng.uniform(0, math.pi * 2)
        self.has_glasses = rng.random() < 0.3
        self.has_hat = rng.random() < 0.2
        self.bubble = SpeechBubbleState()

    def draw(self, surface: pygame.Surface, beat_phase: float):
        x, y = int(self.x), int(self.y)
        s = self.height_scale
        bob = math.sin(beat_phase * math.pi * 2 + self.phase_offset) * 2
        y += int(bob)

        head_r = int(16 * s)
        body_w = int(28 * s)
        body_h = int(45 * s)
        leg_h = int(35 * s)

        # Legs
        pygame.draw.line(surface, (40, 35, 45),
                         (x - int(7 * s), y), (x - int(9 * s), y + leg_h), int(6 * s))
        pygame.draw.line(surface, (40, 35, 45),
                         (x + int(7 * s), y), (x + int(9 * s), y + leg_h), int(6 * s))

        # Shoes
        pygame.draw.ellipse(surface, (35, 30, 30),
                            (x - int(12 * s), y + leg_h - 3, int(12 * s), int(6 * s)))
        pygame.draw.ellipse(surface, (35, 30, 30),
                            (x + int(2 * s), y + leg_h - 3, int(12 * s), int(6 * s)))

        # Body
        pygame.draw.rect(surface, self.shirt,
                         (x - body_w // 2, y - body_h, body_w, body_h),
                         border_radius=int(6 * s))

        # Arms hanging
        arm_sway = math.sin(beat_phase * math.pi * 2 + self.phase_offset) * 3
        pygame.draw.line(surface, self.skin,
                         (x - body_w // 2 - 2, y - body_h + int(12 * s)),
                         (x - body_w // 2 - 5 + int(arm_sway), y - int(8 * s)),
                         int(5 * s))
        pygame.draw.line(surface, self.skin,
                         (x + body_w // 2 + 2, y - body_h + int(12 * s)),
                         (x + body_w // 2 + 5 - int(arm_sway), y - int(8 * s)),
                         int(5 * s))

        # Head
        head_y = y - body_h - head_r + int(5 * s)
        pygame.draw.circle(surface, self.skin, (x, head_y), head_r)

        # Hair
        pygame.draw.arc(surface, self.hair,
                        (x - head_r, head_y - head_r, head_r * 2, head_r * 2),
                        0.4, 2.7, int(4 * s))

        # Hat
        if self.has_hat:
            pygame.draw.rect(surface, self.hair,
                             (x - head_r - 3, head_y - head_r - 2,
                              head_r * 2 + 6, int(8 * s)), border_radius=3)

        # Eyes
        eye_y = head_y - int(2 * s)
        pygame.draw.circle(surface, (35, 25, 20), (x - int(5 * s), eye_y), int(2.5 * s))
        pygame.draw.circle(surface, (35, 25, 20), (x + int(5 * s), eye_y), int(2.5 * s))

        # Glasses
        if self.has_glasses:
            pygame.draw.circle(surface, (60, 60, 70),
                               (x - int(5 * s), eye_y), int(5 * s), 1)
            pygame.draw.circle(surface, (60, 60, 70),
                               (x + int(5 * s), eye_y), int(5 * s), 1)
            pygame.draw.line(surface, (60, 60, 70),
                             (x - int(1 * s), eye_y), (x + int(1 * s), eye_y), 1)

        # Bubble
        self.bubble.draw(surface, x, head_y - head_r - 8)


class CashierVisualizer(BaseVisualizer):

    def __init__(self, surface: pygame.Surface):
        super().__init__(surface)
        self.particles = ParticleSystem(max_particles=200)

        self.timeline_h = 60
        self.scene_h = self.height - self.timeline_h

        # Zoomed-in layout — counter fills lower portion
        self.counter_top_y = int(self.scene_h * 0.55)
        self.counter_front_y = int(self.scene_h * 0.58)
        self.floor_y = int(self.scene_h * 0.88)
        self.conveyor_y = self.counter_top_y - 3

        # Cashier — large, positioned behind the counter
        self.cashier = Cashier(self.width * 0.3, self.counter_top_y - 20)
        self.cashier_bubble = SpeechBubbleState()

        # Scan point
        self.scan_x = int(self.width * 0.48)

        # Conveyor items
        self._items: list[Item] = []
        self._item_speed = 55.0
        self._spawn_timer = 0.0

        # Customers — fewer but bigger, standing in front of counter
        self._customers: list[WaitingCustomer] = []
        for i in range(4):
            cx = self.width * 0.62 + i * 80
            self._customers.append(WaitingCustomer(cx, self.floor_y - 35, i))

        # Performance
        self._recent_good = 0
        self._recent_miss = 0
        self._total_scanned = 0
        self._beat_count = 0

        # Laser
        self._laser_time = 0.0

        # Register screen text
        self._register_text = "$0.00"

        # Timeline
        self.timeline = Timeline(self.surface, self.timeline_h)

        self._label_font = pygame.font.SysFont("consolas", 13, bold=True)
        self._price_font = pygame.font.SysFont("consolas", 11, bold=True)

    def _update_mood(self):
        # Only count items that have passed the scan zone without being scanned
        missed_items = sum(1 for i in self._items if not i.scanned and i.x < self.scan_x - 40)
        net_score = self._recent_good - self._recent_miss * 2

        if net_score >= 6:
            self.cashier.mood = "excited"
        elif net_score >= 3:
            self.cashier.mood = "happy"
        elif net_score <= -3 or missed_items >= 4:
            self.cashier.mood = "grumpy"
        else:
            self.cashier.mood = "bored"

    def on_beat(self, layer: int, beat_idx: int):
        # Spawn item close to the right edge of visible conveyor
        spawn_x = self.width * 0.85 + random.randint(-20, 40)
        self._items.append(Item(spawn_x, self.conveyor_y))
        self._beat_count += 1

        # Decay counters every 6 beats — slow enough to feel progress
        if self._beat_count % 6 == 0:
            self._recent_good = max(0, self._recent_good - 1)
            self._recent_miss = max(0, self._recent_miss - 1)
        self._update_mood()

        # Customers complain based on missed items (passed scan zone unscanned)
        missed_items = sum(1 for i in self._items if not i.scanned and i.x < self.scan_x - 40)
        complaint_chance = min(0.4, missed_items * 0.1)

        if complaint_chance > 0 and random.random() < complaint_chance:
            talkers = [c for c in self._customers if not c.bubble.active]
            if talkers:
                if missed_items >= 4:
                    lines = CUSTOMER_IMPATIENT + [
                        "MANAGER!!", "This is ridiculous!", "I'm leaving!",
                        "Worst cashier ever!", "Open another lane!",
                    ]
                else:
                    lines = CUSTOMER_IMPATIENT
                random.choice(talkers).bubble.say(random.choice(lines), 1.8)

    def on_hit(self, layer: int, rating: str, deviation_ms: float):
        color = rating_color(rating)
        is_good = rating in (HitRating.PERFECT, HitRating.GOOD)

        # Scan nearest item
        best_item = None
        best_dist = 999
        for item in self._items:
            if not item.scanned:
                dist = abs(item.x - self.scan_x)
                if dist < best_dist:
                    best_dist = dist
                    best_item = item

        if best_item:
            best_item.scanned = True
            best_item.scan_time = time.perf_counter()
            self._total_scanned += 1
            self._register_text = f"${self._total_scanned * 2.99:.2f}"

        self.cashier.trigger_scan()
        self._laser_time = time.perf_counter()

        if is_good:
            self._recent_good += 1
            self._item_speed = min(110, self._item_speed + 2)
        elif rating == HitRating.MISS:
            self._recent_miss += 1
            self._item_speed = max(35, self._item_speed - 5)

        self._update_mood()

        # Particles at scan
        count = {HitRating.PERFECT: 12, HitRating.GOOD: 8,
                 HitRating.OK: 4, HitRating.MISS: 2}.get(rating, 4)
        self.particles.emit(self.scan_x, self.conveyor_y - 20,
                            color, count=count, speed=120, life=0.3, size=3)

        # Cashier speech
        if not self.cashier_bubble.active:
            if rating == HitRating.PERFECT and self._recent_good >= 6:
                self.cashier_bubble.say(random.choice(MOOD_EXCITED), 1.5)
            elif is_good and random.random() < 0.3:
                self.cashier_bubble.say(random.choice(MOOD_HAPPY), 1.2)
            elif rating == HitRating.MISS:
                self.cashier_bubble.say(random.choice(MOOD_GRUMPY), 1.5)
            elif rating == HitRating.OK and random.random() < 0.2:
                self.cashier_bubble.say(random.choice(MOOD_BORED), 1.2)

        # Customer reactions
        if rating == HitRating.PERFECT:
            talkers = [c for c in self._customers if not c.bubble.active]
            if talkers and random.random() < 0.4:
                random.choice(talkers).bubble.say(
                    random.choice(CUSTOMER_HAPPY), 1.5)

        # Timeline
        if layer < len(self.layers):
            phases = self.layers[layer]["phases"]
            best_bi = self._find_nearest_beat(phases, self.cycle_phase)
            self.timeline.flash_marker(layer, best_bi, color)
            margin = 40
            mx = margin + int(phases[best_bi] * (self.width - 2 * margin))
            my = self.timeline.row_y(layer, len(self.layers))
            self.particles.emit(mx, my, color, count=8, speed=100, life=0.4)

    def _update_items(self, dt: float):
        for item in self._items:
            item.x -= self._item_speed * dt

        # Items that scroll off unscanned count as misses
        kept = []
        for item in self._items:
            if item.x <= -60:
                if not item.scanned:
                    self._recent_miss += 1
            else:
                kept.append(item)
        self._items = kept

        if self._items:
            self._update_mood()

    def _draw_background(self):
        """Store wall with shelves."""
        self.surface.fill(WALL_COLOR)

        # Shelf rows on back wall
        shelf_color = (45, 38, 50)
        for sy in range(40, int(self.scene_h * 0.45), 70):
            # Shelf plank
            pygame.draw.rect(self.surface, shelf_color,
                             (20, sy, self.width - 40, 6), border_radius=2)
            # Items on shelf (decorative)
            rng = random.Random(sy)
            for sx in range(40, self.width - 40, 35):
                if rng.random() > 0.3:
                    c = rng.choice(ITEM_COLORS)
                    dim = tuple(max(0, v // 3) for v in c)
                    h = rng.randint(12, 25)
                    w = rng.randint(10, 18)
                    pygame.draw.rect(self.surface, dim,
                                     (sx, sy - h, w, h), border_radius=2)

    def _draw_counter(self):
        """Big checkout counter — fills lower third."""
        # Counter top surface
        pygame.draw.rect(self.surface, COUNTER_TOP,
                         (0, self.counter_top_y - 4, int(self.width * 0.55), 8),
                         border_radius=3)

        # Counter front face
        pygame.draw.rect(self.surface, COUNTER_FRONT,
                         (0, self.counter_front_y, int(self.width * 0.55),
                          self.floor_y - self.counter_front_y))

        # Counter edge highlight
        pygame.draw.line(self.surface, (90, 80, 70),
                         (0, self.counter_top_y - 4),
                         (int(self.width * 0.55), self.counter_top_y - 4), 1)

        # Register
        reg_x = int(self.width * 0.22)
        reg_y = self.counter_top_y - 45

        # Register body
        pygame.draw.rect(self.surface, (55, 55, 60),
                         (reg_x, reg_y, 55, 40), border_radius=4)
        # Screen
        screen_c = (30, 70, 30) if self.cashier.mood != "grumpy" else (70, 30, 30)
        pygame.draw.rect(self.surface, screen_c,
                         (reg_x + 4, reg_y + 4, 47, 22), border_radius=3)
        # Price display
        price_surf = self._price_font.render(self._register_text, True, (150, 255, 150))
        self.surface.blit(price_surf, (reg_x + 8, reg_y + 8))

        # Keypad (little dots)
        for ky in range(3):
            for kx in range(3):
                pygame.draw.circle(surface=self.surface, color=(70, 70, 75),
                                   center=(reg_x + 12 + kx * 12, reg_y + 30 + ky * 0),
                                   radius=3)

    def _draw_conveyor(self):
        """Conveyor belt with items."""
        belt_left = int(self.width * 0.44)
        belt_right = self.width + 10
        belt_y = self.conveyor_y

        # Belt surface
        pygame.draw.rect(self.surface, CONVEYOR_COLOR,
                         (belt_left, belt_y, belt_right - belt_left, 10))

        # Rolling belt lines
        scroll = int(time.perf_counter() * self._item_speed) % 25
        for bx in range(belt_left + scroll, belt_right, 25):
            pygame.draw.line(self.surface, CONVEYOR_BELT,
                             (bx, belt_y + 1), (bx, belt_y + 9), 1)

        # Conveyor supports
        for sx in range(belt_left + 50, belt_right - 20, 120):
            pygame.draw.rect(self.surface, (40, 38, 42),
                             (sx, belt_y + 10, 8, self.floor_y - belt_y - 10))

        # Scan zone
        pygame.draw.line(self.surface, (180, 40, 40),
                         (self.scan_x, belt_y - 3), (self.scan_x, belt_y + 12), 2)

        # Laser beam
        laser_age = time.perf_counter() - self._laser_time
        if laser_age < 0.15:
            t = 1.0 - laser_age / 0.15
            lc = (int(255 * t), int(40 * t), int(40 * t))
            pygame.draw.line(self.surface, lc,
                             (self.scan_x, belt_y - 30), (self.scan_x, belt_y + 12), 2)
            # Glow
            gc = (int(80 * t), int(15 * t), int(15 * t))
            pygame.draw.circle(self.surface, gc, (self.scan_x, belt_y - 10), int(12 * t))

        # Items
        for item in self._items:
            item.draw(self.surface)

    def _draw_floor(self):
        """Floor tiles."""
        pygame.draw.rect(self.surface, FLOOR_COLOR,
                         (0, self.floor_y, self.width, self.scene_h - self.floor_y))
        for tx in range(0, self.width, 50):
            shade = 4 if (tx // 50) % 2 == 0 else -4
            c = tuple(max(0, min(255, FLOOR_COLOR[i] + shade)) for i in range(3))
            pygame.draw.rect(self.surface, c,
                             (tx, self.floor_y, 49, self.scene_h - self.floor_y))

    def _draw_scanned_counter(self):
        """Items scanned display."""
        text = f"Scanned: {self._total_scanned}"
        surf = self._label_font.render(text, True, NEON_GREEN)
        self.surface.blit(surf, (15, self.counter_top_y - 50))

    def render(self):
        self._update_items(self.dt)

        self._draw_background()
        self._draw_floor()

        # Customers (behind/beside counter)
        for c in self._customers:
            c.draw(self.surface, self.cycle_phase)

        self._draw_counter()
        self._draw_conveyor()

        # Cashier behind counter
        self.cashier.draw(self.surface, self.cycle_phase)
        self.cashier_bubble.draw(self.surface,
                                  int(self.cashier.base_x),
                                  int(self.cashier.base_y) - 85)

        self._draw_scanned_counter()
        self.timeline.draw(self.layers, self.cycle_phase)

        self.particles.update(self.dt)
        self.particles.draw(self.surface)

        bloom = bloom_pass(self.surface, scale=6)
        self.surface.blit(bloom, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
