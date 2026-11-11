#!/usr/bin/env python3
"""Photo restoration with Real-ESRGAN realesr-general-x4v3 (the engine family
Upscayl is built on), CPU via ONNX Runtime.

restore(img) upscales x4 tile by tile and keeps the large result (up to MAX_W):
compression blocks and blur from Telegram are cleaned up, edges get crisper.
The result is blended with the original (BLEND) so it never looks plastic.
"""
from pathlib import Path

import numpy as np
from PIL import Image

MODEL = Path(__file__).resolve().parent / "models" / "realesr-general-x4v3.onnx"
TILE, PAD, SCALE = 256, 12, 4
BLEND = 0.75          # share of the restored image in the result
_sess = None


def _session():
    global _sess
    if _sess is None:
        import onnxruntime as ort
        _sess = ort.InferenceSession(str(MODEL), providers=["CPUExecutionProvider"])
    return _sess


def upscale_x4(img):
    a = np.asarray(img.convert("RGB"), dtype=np.float32).transpose(2, 0, 1) / 255.0
    _, h, w = a.shape
    out = np.zeros((3, h * SCALE, w * SCALE), dtype=np.float32)
    s = _session(); name = s.get_inputs()[0].name
    for y in range(0, h, TILE):
        for x in range(0, w, TILE):
            y0, x0 = max(0, y - PAD), max(0, x - PAD)
            y1, x1 = min(h, y + TILE + PAD), min(w, x + TILE + PAD)
            res = s.run(None, {name: a[None, :, y0:y1, x0:x1]})[0][0]
            ty, tx = (y - y0) * SCALE, (x - x0) * SCALE
            th, tw = (min(h, y + TILE) - y) * SCALE, (min(w, x + TILE) - x) * SCALE
            out[:, y * SCALE:y * SCALE + th, x * SCALE:x * SCALE + tw] = res[:, ty:ty + th, tx:tx + tw]
    return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype("uint8").transpose(1, 2, 0))


MAX_W = 2400          # keep the upscaled photo up to this width (story cards are ~950 px wide)


def restore(img, blend=BLEND, max_w=MAX_W):
    """x4 Real-ESRGAN, KEPT at high resolution (up to max_w), blended with a plain
    Lanczos enlargement so it stays natural. Before 12.11.2026 the result was scaled back
    to the original size, so small photos (e.g. 640 px car photos) were enlarged later
    by plain resizing and looked soft."""
    img = img.convert("RGB")
    big = upscale_x4(img)
    w = min(big.width, max(max_w, img.width))
    h = round(big.height * w / big.width)
    big = big.resize((w, h), Image.LANCZOS)
    if blend >= 1:
        return big
    plain = img.resize((w, h), Image.LANCZOS)
    return Image.blend(plain, big, blend)
