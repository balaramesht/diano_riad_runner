import os
import math
import random
from array import array
from typing import Dict, Optional

import pygame


class SoundManager:
    """Centralized sound synthesis/loading and playback.

    Prefers files in `sounds/` if present; otherwise synthesizes simple tones.
    Manages dedicated channels for background music and the running loop.
    """

    def __init__(self) -> None:
        # Ensure mixer is initialized and discover format
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        freq, _fmt, _channels = pygame.mixer.get_init()
        self.sample_rate: int = freq or 22050

        # Channels
        pygame.mixer.set_num_channels(max(8, pygame.mixer.get_num_channels()))
        self.channel_run = pygame.mixer.Channel(0)
        self.channel_music = pygame.mixer.Channel(1)
        self.channel_run.set_volume(0.18)
        self.channel_music.set_volume(0.12)

        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self._load_or_synthesize_sounds()

    # -----------------------------
    # Public API
    # -----------------------------
    def start_run_loop(self) -> None:
        snd = self.sounds.get("run")
        if snd and not self.channel_run.get_busy():
            self.channel_run.play(snd, loops=-1)

    def stop_run_loop(self) -> None:
        if self.channel_run.get_busy():
            self.channel_run.stop()

    def start_music(self) -> None:
        snd = self.sounds.get("music")
        if snd and not self.channel_music.get_busy():
            self.channel_music.play(snd, loops=-1)

    def stop_music(self) -> None:
        if self.channel_music.get_busy():
            self.channel_music.stop()

    def play(self, name: str) -> None:
        snd = self.sounds.get(name)
        if snd is not None:
            snd.play()

    # -----------------------------
    # Loading and synthesis
    # -----------------------------
    def _load_or_synthesize_sounds(self) -> None:
        sounds_dir = os.path.join(os.path.dirname(__file__), "sounds")

        def load_if_exists(key: str, filename: str) -> Optional[pygame.mixer.Sound]:
            path = os.path.join(sounds_dir, filename)
            return pygame.mixer.Sound(path) if os.path.exists(path) else None

        # Try file-based first
        file_map = {
            "run": "run.wav",
            "jump": "jump.wav",
            "land": "land.wav",
            "duck": "duck.wav",
            "spawn": "spawn.wav",
            "milestone": "milestone.wav",
            "game_over": "game_over.wav",
            "restart": "restart.wav",
            "music": "music.wav",
        }
        for key, fname in file_map.items():
            snd = load_if_exists(key, fname)
            if snd is not None:
                self.sounds[key] = snd

        # Synthesize any that are missing
        if "run" not in self.sounds:
            self.sounds["run"] = self._synth_footstep_loop()
        if "jump" not in self.sounds:
            self.sounds["jump"] = self._synth_jump()
        if "land" not in self.sounds:
            self.sounds["land"] = self._synth_land()
        if "duck" not in self.sounds:
            self.sounds["duck"] = self._synth_duck()
        if "spawn" not in self.sounds:
            self.sounds["spawn"] = self._synth_pop()
        if "milestone" not in self.sounds:
            self.sounds["milestone"] = self._synth_milestone()
        if "game_over" not in self.sounds:
            self.sounds["game_over"] = self._synth_game_over()
        if "restart" not in self.sounds:
            self.sounds["restart"] = self._synth_restart()
        if "music" not in self.sounds:
            self.sounds["music"] = self._synth_music_loop()

    # -----------------------------
    # Synthesis helpers
    # -----------------------------
    def _to_sound(self, samples: array) -> pygame.mixer.Sound:
        # Ensure 16-bit signed little-endian mono
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def _render_sine(self, frequency_hz: float, duration_sec: float, volume: float = 0.5) -> array:
        total = int(self.sample_rate * duration_sec)
        data = array("h")
        two_pi_f_over_sr = 2.0 * math.pi * frequency_hz / self.sample_rate
        amplitude = int(max(0.0, min(1.0, volume)) * 32767)
        for i in range(total):
            sample = int(math.sin(i * two_pi_f_over_sr) * amplitude)
            data.append(sample)
        return data

    def _render_square(self, frequency_hz: float, duration_sec: float, volume: float = 0.5) -> array:
        total = int(self.sample_rate * duration_sec)
        period = max(1, int(self.sample_rate / frequency_hz))
        high = int(max(0.0, min(1.0, volume)) * 32767)
        low = -high
        data = array("h")
        for i in range(total):
            data.append(high if (i % period) < (period // 2) else low)
        return data

    def _render_noise(self, duration_sec: float, volume: float = 0.5) -> array:
        total = int(self.sample_rate * duration_sec)
        amp = int(max(0.0, min(1.0, volume)) * 32767)
        data = array("h")
        rng = random.Random(42)
        for _ in range(total):
            data.append(rng.randint(-amp, amp))
        return data

    def _render_sweep(self, start_freq: float, end_freq: float, duration_sec: float, volume: float = 0.5) -> array:
        total = int(self.sample_rate * duration_sec)
        data = array("h")
        amp = int(max(0.0, min(1.0, volume)) * 32767)
        for i in range(total):
            t = i / self.sample_rate
            # Linear frequency sweep
            freq = start_freq + (end_freq - start_freq) * (t / duration_sec)
            phase = 2.0 * math.pi * freq * t
            data.append(int(math.sin(phase) * amp))
        return data

    @staticmethod
    def _mix(a: array, b: array, gain_a: float = 1.0, gain_b: float = 1.0) -> array:
        n = max(len(a), len(b))
        out = array("h")
        for i in range(n):
            sa = a[i] if i < len(a) else 0
            sb = b[i] if i < len(b) else 0
            val = int(sa * gain_a + sb * gain_b)
            # Clip to 16-bit signed
            val = max(-32768, min(32767, val))
            out.append(val)
        return out

    @staticmethod
    def _concat(parts: list[array]) -> array:
        out = array("h")
        for p in parts:
            out.extend(p)
        return out

    # -----------------------------
    # Specific SFX synthesis
    # -----------------------------
    def _synth_footstep(self) -> array:
        # Low thump with quick decay
        base = self._render_sine(140.0, 0.08, volume=0.6)
        noise = self._render_noise(0.06, volume=0.2)
        return self._mix(base, noise, 1.0, 0.6)

    def _synth_footstep_loop(self) -> pygame.mixer.Sound:
        # Two footsteps per beat
        step1 = self._synth_footstep()
        silence = array("h", [0] * int(self.sample_rate * 0.10))
        step2 = self._synth_footstep()
        loop = self._concat([step1, silence, step2, silence])
        return self._to_sound(loop)

    def _synth_jump(self) -> pygame.mixer.Sound:
        up = self._render_sweep(300.0, 1200.0, 0.22, volume=0.45)
        return self._to_sound(up)

    def _synth_land(self) -> pygame.mixer.Sound:
        thump = self._synth_footstep()
        return self._to_sound(thump)

    def _synth_duck(self) -> pygame.mixer.Sound:
        down = self._render_sweep(800.0, 300.0, 0.14, volume=0.40)
        return self._to_sound(down)

    def _synth_pop(self) -> pygame.mixer.Sound:
        pop = self._render_square(600.0, 0.05, volume=0.35)
        return self._to_sound(pop)

    def _synth_milestone(self) -> pygame.mixer.Sound:
        a5 = self._render_sine(880.0, 0.08, volume=0.35)
        d6 = self._render_sine(1174.66, 0.10, volume=0.35)
        return self._to_sound(self._concat([a5, d6]))

    def _synth_game_over(self) -> pygame.mixer.Sound:
        fall = self._render_sweep(400.0, 80.0, 0.35, volume=0.40)
        noise = self._render_noise(0.30, volume=0.20)
        mixed = self._mix(fall, noise, 1.0, 1.0)
        return self._to_sound(mixed)

    def _synth_restart(self) -> pygame.mixer.Sound:
        up1 = self._render_sine(660.0, 0.06, volume=0.30)
        up2 = self._render_sine(880.0, 0.10, volume=0.30)
        return self._to_sound(self._concat([up1, up2]))

    def _synth_music_loop(self) -> pygame.mixer.Sound:
        # Simple gentle pad: low-volume layered sines for a short seamless loop
        base = self._render_sine(220.0, 1.6, volume=0.08)
        fifth = self._render_sine(330.0, 1.6, volume=0.06)
        high = self._render_sine(440.0, 1.6, volume=0.04)
        pad = self._mix(self._mix(base, fifth), high)
        return self._to_sound(pad)

    # Convenience hook for game over event
    def on_game_over(self) -> None:
        self.stop_run_loop()
        self.play("game_over")