#!/usr/bin/env python3
"""Animated version of a collage story (MP4, 1080x1920, 30 fps, no sound).

Timeline (8 s):
  0.0-0.6  background and text fade in from black
  0.3-1.1  upper card slides in from the right
  0.6-1.4  main card slides in from the left
  then     both photos slowly push in towards the bike (Ken Burns)
  last 0.4 s holds the final frame
Music is added in Instagram as before.
"""
import subprocess

from PIL import Image

import make_story as ms

FPS = 30
DURATION = 8.0


def _ease_out(t):
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def render_video(args, out_path, duration=DURATION, fps=FPS):
    base, cards = ms.compose(args)
    if not cards:
        raise ValueError("video is made for the card collage layout only")
    black = Image.new("RGB", base.size, (0, 0, 0))
    n = int(duration * fps)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{ms.W}x{ms.H}", "-r", str(fps), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", str(out_path)]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    starts = [(0.3, +1), (0.6, -1)]            # (start time, slide direction) per card
    hold = duration - 0.4
    for k in range(n):
        t = k / fps
        fade = _ease_out(t / 0.6)
        frame = Image.blend(black, base, fade) if fade < 1 else base.copy()
        zoom = 1.0 + 0.07 * min(t, hold) / hold
        for (spec, x, y), (t0, side) in zip(cards, starts):
            p = _ease_out((t - t0) / 0.8)
            if p <= 0:
                continue
            dx = int(side * (1 - p) * (ms.W - x + 40))
            frame.paste(ms.card_image(spec, zoom), (x + dx, y), spec["mask"])
        enc.stdin.write(frame.tobytes())
    enc.stdin.close()
    if enc.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    return out_path
