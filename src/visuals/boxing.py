"""Boxing ring visualizer.

Two fighters throw jabs and defend according to the rhythm.
Player hits control the left fighter — accuracy determines punch quality.
A crowd in the back cheers and bounces with the beat.
"""

import math
import random
import time
import pygame
from src.visuals.base import BaseVisualizer
from src.visuals.colors import (
    BG_DARK, CYAN, MAGENTA, NEON_GREEN, HOT_PINK,
    YELLOW, ORANGE, PURPLE, rating_color
)
from src.visuals.effects import bloom_pass, ParticleSystem
from src.visuals.timeline import Timeline
from src.engine.scoring import HitRating


# Colors
RING_FLOOR = (30, 15, 40)
RING_ROPE = (200, 50, 50)
RING_POST = (160, 140, 60)
CROWD_COLORS = [
    (80, 50, 120), (100, 60, 140), (70, 45, 110), (110, 70, 150),
    (90, 55, 130), (75, 50, 115), (95, 65, 135), (60, 40, 100),
]
SKIN_L = (220, 180, 140)
SKIN_R = (180, 140, 110)
GLOVE_L = CYAN
GLOVE_R = HOT_PINK
SHORTS_L = (0, 150, 255)
SHORTS_R = (255, 50, 50)


class Fighter:
    """Simple geometric fighter with punch/block/idle animations."""

    def __init__(self, x: float, y: float, facing: int, skin: tuple,
                 glove_color: tuple, shorts_color: tuple):
        self.base_x = x
        self.base_y = y
        self.facing = facing  # 1 = facing right, -1 = facing left

        self.skin = skin
        self.glove_color = glove_color
        self.shorts_color = shorts_color

        # Animation state
        self.state = "idle"
        self.state_time = 0.0
        self.state_duration = 0.3

    def set_state(self, state: str, duration: float = 0.3):
        self.state = state
        self.state_time = time.perf_counter()
        self.state_duration = duration

    def _anim_t(self) -> float:
        elapsed = time.perf_counter() - self.state_time
        t = min(1.0, elapsed / self.state_duration) if self.state_duration > 0 else 1.0
        if t >= 1.0:
            self.state = "idle"
        return t

    def draw(self, surface: pygame.Surface, beat_phase: float):
        t = self._anim_t()
        f = self.facing

        # Idle bob with beat
        bob = math.sin(beat_phase * math.pi * 2) * 4

        bx = self.base_x
        by = self.base_y + bob

        # State-driven offsets
        punch_extend = 0.0
        block_raise = 0.0

        if self.state == "jab":
            # Lunge forward with full arm extension
            punch_extend = math.sin(t * math.pi) * 60
            bx += f * punch_extend * 0.5
        elif self.state == "hook":
            # Wider arc
            punch_extend = math.sin(t * math.pi) * 50
            bx += f * punch_extend * 0.4
        elif self.state == "block":
            block_raise = math.sin(t * math.pi) * 20
        elif self.state == "recoil":
            # Snap back hard
            snap = math.sin(t * math.pi)
            bx -= f * snap * 30
            by += snap * 8
        elif self.state == "dodge":
            duck = math.sin(t * math.pi)
            by += duck * 30
            bx -= f * duck * 20

        cx = int(bx)
        cy = int(by)

        # Dimensions
        head_r = 16
        body_w = 26
        body_h = 40
        leg_h = 32

        # --- Legs ---
        leg_y = cy + body_h // 2
        pygame.draw.line(surface, self.skin,
                         (cx - 9, leg_y), (cx - 12, leg_y + leg_h), 5)
        pygame.draw.line(surface, self.skin,
                         (cx + 9, leg_y), (cx + 12, leg_y + leg_h), 5)
        # Shoes
        pygame.draw.circle(surface, (40, 30, 30), (cx - 12, leg_y + leg_h), 5)
        pygame.draw.circle(surface, (40, 30, 30), (cx + 12, leg_y + leg_h), 5)

        # --- Shorts ---
        pygame.draw.rect(surface, self.shorts_color,
                         (cx - body_w // 2, cy + 5, body_w, body_h // 2),
                         border_radius=4)

        # --- Torso ---
        pygame.draw.rect(surface, self.skin,
                         (cx - body_w // 2, cy - body_h // 2 + 5, body_w, body_h // 2 + 5),
                         border_radius=6)

        # --- Arms & gloves ---
        shoulder_y = cy - body_h // 2 + 16

        # Back arm (guard position)
        back_arm_x = cx - f * 12
        back_glove_x = back_arm_x - f * 6
        back_glove_y = shoulder_y + 5 - int(block_raise)
        pygame.draw.line(surface, self.skin,
                         (back_arm_x, shoulder_y),
                         (int(back_glove_x), int(back_glove_y)), 5)
        pygame.draw.circle(surface, self.glove_color,
                           (int(back_glove_x), int(back_glove_y)), 10)

        # Front arm (punching arm)
        front_arm_x = cx + f * 12
        front_glove_y = shoulder_y - 8 - int(block_raise)
        front_glove_x = front_arm_x + f * (18 + int(punch_extend))
        pygame.draw.line(surface, self.skin,
                         (front_arm_x, shoulder_y),
                         (int(front_glove_x), int(front_glove_y)), 5)
        pygame.draw.circle(surface, self.glove_color,
                           (int(front_glove_x), int(front_glove_y)), 11)

        # --- Head ---
        head_y = cy - body_h // 2 - head_r + 8
        pygame.draw.circle(surface, self.skin, (cx, int(head_y)), head_r)
        # Eyes
        eye_x = cx + f * 5
        pygame.draw.circle(surface, (30, 20, 20), (eye_x, int(head_y) - 2), 3)
        # Mouth line
        mouth_y = int(head_y) + 6
        if self.state == "recoil":
            # Open mouth on hit
            pygame.draw.circle(surface, (30, 20, 20), (cx + f * 2, mouth_y), 4)
        else:
            pygame.draw.line(surface, (30, 20, 20),
                             (cx + f * 1, mouth_y), (cx + f * 7, mouth_y), 2)

        return int(front_glove_x), int(front_glove_y)


class CrowdMember:
    """A single crowd member that bounces with the beat."""

    def __init__(self, x: float, y: float, color: tuple, size: float):
        self.x = x
        self.y = y
        self.base_y = y
        self.color = color
        self.size = size
        # Offset so not all crowd members bounce in perfect sync
        self.phase_offset = random.uniform(-0.08, 0.08)
        self.cheer_intensity = 0.0  # 0-1, decays over time
        self.cheer_time = 0.0

    def draw(self, surface: pygame.Surface, beat_phase: float):
        # All crowd bounces with the beat, offset slightly
        phase = beat_phase + self.phase_offset
        bounce = math.sin(phase * math.pi * 2) * (3 + self.cheer_intensity * 4)
        y = int(self.base_y + bounce)
        x = int(self.x)
        s = int(self.size)

        # Cheer intensity decays
        age = time.perf_counter() - self.cheer_time
        if age < 0.8:
            self.cheer_intensity = max(0, 1.0 - age / 0.8)
        else:
            self.cheer_intensity = 0.0

        cheering = self.cheer_intensity > 0.3

        # Head
        pygame.draw.circle(surface, self.color, (x, y - s), s)
        # Body
        pygame.draw.rect(surface, self.color,
                         (x - s // 2, y - s // 2, s, s + 6))

        if cheering:
            # Arms up, waving
            wave = math.sin(time.perf_counter() * 12 + self.phase_offset * 50) * 4
            pygame.draw.line(surface, self.color,
                             (x - s, y), (x - s - 4, y - s - 6 + int(wave)), 2)
            pygame.draw.line(surface, self.color,
                             (x + s, y), (x + s + 4, y - s - 6 - int(wave)), 2)
        else:
            # Arms down, slight sway
            sway = math.sin(phase * math.pi * 2) * 2
            pygame.draw.line(surface, self.color,
                             (x - s, y), (x - s - 2 + int(sway), y + 6), 2)
            pygame.draw.line(surface, self.color,
                             (x + s, y), (x + s + 2 - int(sway), y + 6), 2)


class RingCharacter:
    """A non-fighting character in the ring scene (referee or coach).

    Drawn as a simple figure that bobs with the beat and reacts to action.
    """

    def __init__(self, x: float, y: float, shirt_color: tuple,
                 pants_color: tuple, skin: tuple, scale: float = 1.0):
        self.base_x = x
        self.base_y = y
        self.shirt_color = shirt_color
        self.pants_color = pants_color
        self.skin = skin
        self.scale = scale

        # Animation
        self.lean_x = 0.0  # Lean left/right to watch action
        self.arm_raise = 0.0  # 0-1, raise arms (coach encouragement)
        self.arm_raise_time = 0.0

    def set_arm_raise(self, duration: float = 0.4):
        self.arm_raise_time = time.perf_counter()
        self.arm_raise = duration

    def draw(self, surface: pygame.Surface, beat_phase: float):
        s = self.scale
        bob = math.sin(beat_phase * math.pi * 2) * 3 * s

        cx = int(self.base_x + self.lean_x)
        cy = int(self.base_y + bob)

        # Arm raise decay
        arm_t = 0.0
        if self.arm_raise > 0:
            age = time.perf_counter() - self.arm_raise_time
            if age < self.arm_raise:
                arm_t = math.sin((age / self.arm_raise) * math.pi)

        head_r = int(10 * s)
        body_w = int(18 * s)
        body_h = int(28 * s)
        leg_h = int(22 * s)

        # Legs
        pygame.draw.line(surface, self.pants_color,
                         (cx - int(6 * s), cy + body_h // 2),
                         (cx - int(8 * s), cy + body_h // 2 + leg_h), int(4 * s))
        pygame.draw.line(surface, self.pants_color,
                         (cx + int(6 * s), cy + body_h // 2),
                         (cx + int(8 * s), cy + body_h // 2 + leg_h), int(4 * s))

        # Body
        pygame.draw.rect(surface, self.shirt_color,
                         (cx - body_w // 2, cy - body_h // 2, body_w, body_h),
                         border_radius=int(4 * s))

        # Arms
        shoulder_y = cy - body_h // 2 + int(10 * s)
        arm_up_offset = int(arm_t * 20 * s)

        pygame.draw.line(surface, self.skin,
                         (cx - body_w // 2, shoulder_y),
                         (cx - body_w // 2 - int(10 * s),
                          shoulder_y + int(12 * s) - arm_up_offset),
                         int(3 * s))
        pygame.draw.line(surface, self.skin,
                         (cx + body_w // 2, shoulder_y),
                         (cx + body_w // 2 + int(10 * s),
                          shoulder_y + int(12 * s) - arm_up_offset),
                         int(3 * s))

        # Head
        head_y = cy - body_h // 2 - head_r + int(4 * s)
        pygame.draw.circle(surface, self.skin, (cx, int(head_y)), head_r)
        # Eye (looking toward center of ring)
        look_dir = 1 if self.lean_x < 0 else -1
        pygame.draw.circle(surface, (30, 20, 20),
                           (cx + look_dir * int(3 * s), int(head_y) - int(1 * s)),
                           int(2 * s))


class BoxingVisualizer(BaseVisualizer):

    def __init__(self, surface: pygame.Surface):
        super().__init__(surface)
        self.particles = ParticleSystem()

        self.timeline_h = 60
        self.ring_h = self.height - self.timeline_h

        # Ring dimensions
        self.ring_left = int(self.width * 0.15)
        self.ring_right = int(self.width * 0.85)
        self.ring_top = int(self.ring_h * 0.35)
        self.ring_bottom = int(self.ring_h * 0.85)
        self.ring_cx = self.width // 2
        self.ring_cy = (self.ring_top + self.ring_bottom) // 2

        # Fighters — close together so punches connect
        fighter_y = self.ring_cy + 10
        gap = 50  # Distance between fighters
        self.fighter_l = Fighter(
            self.ring_cx - gap, fighter_y, 1,
            SKIN_L, GLOVE_L, SHORTS_L
        )
        self.fighter_r = Fighter(
            self.ring_cx + gap, fighter_y, -1,
            SKIN_R, GLOVE_R, SHORTS_R
        )

        # Referee — stands further back behind fighters, full size
        self.referee = RingCharacter(
            self.ring_cx, fighter_y - 50,
            shirt_color=(220, 220, 220),
            pants_color=(30, 30, 30),
            skin=(200, 165, 130),
            scale=1.0
        )

        # Coaches — outside the ring, same height and size as fighters
        self.coach_l = RingCharacter(
            self.ring_left - 40, fighter_y,
            shirt_color=SHORTS_L,
            pants_color=(30, 30, 50),
            skin=(210, 170, 130),
            scale=1.0
        )
        self.coach_r = RingCharacter(
            self.ring_right + 40, fighter_y,
            shirt_color=SHORTS_R,
            pants_color=(30, 30, 50),
            skin=(170, 130, 100),
            scale=1.0
        )

        # Crowd
        self.crowd: list[CrowdMember] = []
        self._generate_crowd()

        # Opponent action cycle
        self._opponent_actions = ["block", "dodge", "idle", "jab", "block", "idle"]
        self._opponent_idx = 0

        # Timeline
        self.timeline = Timeline(self.surface, self.timeline_h)

        # Impact flash
        self._impact_time = 0.0
        self._impact_pos = (0, 0)
        self._impact_color = CYAN

        # Cached font
        self._label_font = pygame.font.SysFont("consolas", 12, bold=True)

    def _generate_crowd(self):
        crowd_top = int(self.ring_h * 0.05)
        crowd_bottom = self.ring_top + 15

        for _ in range(80):
            x = random.randint(15, self.width - 15)
            y = random.randint(crowd_top, crowd_bottom)
            depth = (y - crowd_top) / max(1, crowd_bottom - crowd_top)
            size = int(4 + depth * 6)
            base = random.choice(CROWD_COLORS)
            bright = random.uniform(0.7, 1.4)
            color = tuple(min(255, int(c * bright)) for c in base)
            self.crowd.append(CrowdMember(x, y, color, size))

        self.crowd.sort(key=lambda c: c.base_y)

    def _cheer_crowd(self, intensity: float):
        """Make a portion of the crowd cheer. intensity 0-1."""
        n = int(len(self.crowd) * intensity)
        for c in random.sample(self.crowd, min(n, len(self.crowd))):
            c.cheer_time = time.perf_counter()
            c.cheer_intensity = intensity

    def on_hit(self, layer: int, rating: str, deviation_ms: float):
        color = rating_color(rating)

        if rating == HitRating.PERFECT:
            self.fighter_l.set_state("jab", 0.2)
            self.fighter_r.set_state("recoil", 0.35)
            ix = int(self.ring_cx + 15)
            iy = int(self.fighter_r.base_y - 35)
            self._impact_time = time.perf_counter()
            self._impact_pos = (ix, iy)
            self._impact_color = color
            self.particles.emit(ix, iy, color, count=20, speed=250, life=0.5, size=5)
            self._cheer_crowd(0.9)
            self.referee.lean_x = 25  # Lean toward hit
            self.coach_l.set_arm_raise(0.5)  # Player's coach celebrates

        elif rating == HitRating.GOOD:
            self.fighter_l.set_state("jab", 0.2)
            self.fighter_r.set_state("block", 0.3)
            ix = int(self.ring_cx + 20)
            iy = int(self.fighter_r.base_y - 20)
            self._impact_time = time.perf_counter()
            self._impact_pos = (ix, iy)
            self._impact_color = color
            self.particles.emit(ix, iy, color, count=12, speed=150, life=0.3, size=3)
            self._cheer_crowd(0.5)
            self.referee.lean_x = 15
            self.coach_l.set_arm_raise(0.3)

        elif rating == HitRating.OK:
            self.fighter_l.set_state("hook", 0.25)
            self.fighter_r.set_state("block", 0.3)
            self.particles.emit(self.ring_cx + 10, int(self.fighter_r.base_y - 15),
                                color, count=6, speed=100, life=0.2)
            self._cheer_crowd(0.2)

        else:  # MISS
            self.fighter_l.set_state("jab", 0.2)
            self.fighter_r.set_state("dodge", 0.3)

        # Timeline marker flash
        if layer < len(self.layers):
            phases = self.layers[layer]["phases"]
            best_bi = self._find_nearest_beat(phases, self.cycle_phase)
            self.timeline.flash_marker(layer, best_bi, color)
            margin = 40
            mx = margin + int(phases[best_bi] * (self.width - 2 * margin))
            my = self.timeline.row_y(layer, len(self.layers))
            self.particles.emit(mx, my, color, count=10, speed=120, life=0.5)

    def on_beat(self, layer: int, beat_idx: int):
        # Every beat: crowd gets a small bounce boost
        self._cheer_crowd(0.15)

        # Opponent throws on their layer's beats occasionally
        if layer > 0 or (layer == 0 and len(self.layers) == 1):
            if self.fighter_r.state == "idle":
                action = self._opponent_actions[self._opponent_idx % len(self._opponent_actions)]
                self._opponent_idx += 1
                if action == "jab":
                    self.fighter_r.set_state("jab", 0.2)
                    self.fighter_l.set_state("block", 0.3)
                    # Small impact on player
                    ix = int(self.ring_cx - 15)
                    iy = int(self.fighter_l.base_y - 20)
                    self._impact_time = time.perf_counter()
                    self._impact_pos = (ix, iy)
                    self._impact_color = GLOVE_R
                    self.particles.emit(ix, iy, GLOVE_R, count=6, speed=100, life=0.2, size=3)
                    self.referee.lean_x = -20  # Lean toward player
                    self.coach_r.set_arm_raise(0.4)  # Opponent's coach encourages

    def _draw_crowd(self, beat_phase: float):
        for member in self.crowd:
            member.draw(self.surface, beat_phase)

    def _draw_ring(self):
        rl, rr = self.ring_left, self.ring_right
        rt, rb = self.ring_top, self.ring_bottom

        # Floor
        floor_points = [
            (rl - 20, rb + 10), (rr + 20, rb + 10),
            (rr - 30, rt), (rl + 30, rt),
        ]
        pygame.draw.polygon(self.surface, RING_FLOOR, floor_points)
        pygame.draw.polygon(self.surface, (50, 25, 65), floor_points, 2)

        # Corner posts
        post_w = 6
        for px, py_top in [(rl + 30, rt), (rr - 30, rt),
                            (rl - 10, rb + 5), (rr + 10, rb + 5)]:
            pygame.draw.rect(self.surface, RING_POST,
                             (px - post_w // 2, py_top - 40, post_w, 45))

        # Back and side ropes
        for rope_frac in [0.25, 0.5, 0.75]:
            ry_back = int(rt - 40 + rope_frac * 40)
            ry_front = int(rb + 5 - 35 + rope_frac * 40)
            # Back
            pygame.draw.line(self.surface, RING_ROPE,
                             (rl + 30, ry_back), (rr - 30, ry_back), 2)
            # Sides
            pygame.draw.line(self.surface, RING_ROPE,
                             (rl + 30, ry_back), (rl - 10, ry_front), 2)
            pygame.draw.line(self.surface, RING_ROPE,
                             (rr - 30, ry_back), (rr + 10, ry_front), 2)

    def _draw_front_ropes(self):
        rl, rr = self.ring_left, self.ring_right
        rb = self.ring_bottom
        for rope_frac in [0.25, 0.5, 0.75]:
            ry = int(rb + 5 - 35 + rope_frac * 40)
            pygame.draw.line(self.surface, RING_ROPE,
                             (rl - 10, ry), (rr + 10, ry), 2)

    def _draw_impact(self):
        age = time.perf_counter() - self._impact_time
        if age > 0.25:
            return
        t = 1.0 - age / 0.25
        ix, iy = self._impact_pos
        color = self._impact_color[:3]

        # Expanding circles drawn directly (no surface = no square edges)
        r_outer = int(15 + 20 * (1 - t))
        r_inner = max(2, int(r_outer * 0.4))
        dim = tuple(int(c * t * 0.6) for c in color)
        bright = tuple(min(255, int(c * t)) for c in color)
        pygame.draw.circle(self.surface, dim, (ix, iy), r_outer, 2)
        pygame.draw.circle(self.surface, bright, (ix, iy), r_inner)

        # Impact text
        if age < 0.15:
            words = ["POW!", "BAM!", "WHACK!", "CRACK!"]
            word = words[int(self._impact_time * 7) % len(words)]
            text_color = tuple(min(255, int(c * (1 - age / 0.15))) for c in color)
            text_surf = self._label_font.render(word, True, text_color)
            self.surface.blit(text_surf, (ix - text_surf.get_width() // 2,
                                           iy - 30 - int(age * 80)))

    def _draw_labels(self):
        label_l = self._label_font.render("YOU", True, GLOVE_L)
        label_r = self._label_font.render("CPU", True, GLOVE_R)
        self.surface.blit(label_l, (int(self.fighter_l.base_x) - label_l.get_width() // 2,
                                     self.ring_bottom - 5))
        self.surface.blit(label_r, (int(self.fighter_r.base_x) - label_r.get_width() // 2,
                                     self.ring_bottom - 5))

    def _draw_timeline(self):
        self.timeline.draw(self.layers, self.cycle_phase)

    def render(self):
        self.surface.fill((10, 5, 18))

        # Referee lean decays toward center
        self.referee.lean_x *= 0.93

        self._draw_crowd(self.cycle_phase)
        self._draw_ring()

        # Referee behind fighters
        self.referee.draw(self.surface, self.cycle_phase)

        self.fighter_l.draw(self.surface, self.cycle_phase)
        self.fighter_r.draw(self.surface, self.cycle_phase)
        self._draw_impact()
        self._draw_front_ropes()

        # Coaches outside the ropes (drawn over front ropes)
        self.coach_l.draw(self.surface, self.cycle_phase)
        self.coach_r.draw(self.surface, self.cycle_phase)

        self._draw_labels()
        self._draw_timeline()

        self.particles.update(self.dt)
        self.particles.draw(self.surface)

        bloom = bloom_pass(self.surface, scale=4)
        self.surface.blit(bloom, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
