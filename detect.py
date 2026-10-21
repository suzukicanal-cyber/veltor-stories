#!/usr/bin/env python3
"""Find the motorcycle on a photo with a small YOLO11n detector (ONNX, COCO classes)
and tell a whole-bike shot from a detail / close-up shot.

whole_score(photo) -> 0..1: high when one motorcycle is clearly visible, large and
not cut off by the frame; 0 when no motorcycle is found (detail shot).
"""
from pathlib import Path

import numpy as np
from PIL import Image

MODEL = Path(__file__).resolve().parent / "models" / "yolo11n.onnx"
MOTORCYCLE = 3          # COCO class id
CONF = 0.30
_session = None


def _sess():
    global _session
    if _session is None:
        import onnxruntime as ort
        _session = ort.InferenceSession(str(MODEL), providers=["CPUExecutionProvider"])
    return _session


def motorcycle_boxes(path):
    """Motorcycle boxes as (x0, y0, x1, y1, conf) in 0..1 image coordinates."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    s = 640 / max(w, h)
    nw, nh = round(w * s), round(h * s)
    canvas = Image.new("RGB", (640, 640), (114, 114, 114))
    px, py = (640 - nw) // 2, (640 - nh) // 2
    canvas.paste(im.resize((nw, nh), Image.BILINEAR), (px, py))
    x = np.asarray(canvas, dtype=np.float32).transpose(2, 0, 1)[None] / 255.0
    out = _sess().run(None, {_sess().get_inputs()[0].name: x})[0][0]   # (84, 8400)
    scores = out[4 + MOTORCYCLE]
    keep = scores > CONF
    boxes = []
    for (cx, cy, bw, bh), c in zip(out[:4, keep].T, scores[keep]):
        x0, y0 = (cx - bw / 2 - px) / s / w, (cy - bh / 2 - py) / s / h
        x1, y1 = (cx + bw / 2 - px) / s / w, (cy + bh / 2 - py) / s / h
        boxes.append((max(0, x0), max(0, y0), min(1, x1), min(1, y1), float(c)))
    boxes.sort(key=lambda b: -b[4])
    picked = []                                   # simple NMS
    for b in boxes:
        if all(_iou(b, p) < 0.5 for p in picked):
            picked.append(b)
    return picked


def _iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter + 1e-9)


def whole_score(path):
    """How well the photo shows ONE whole motorcycle large in the frame."""
    boxes = motorcycle_boxes(path)
    if not boxes:
        return 0.0, None
    b = max(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]) * b[4])
    area = (b[2] - b[0]) * (b[3] - b[1])
    edges = sum([b[0] < 0.015, b[1] < 0.015, b[2] > 0.985, b[3] > 0.985])
    if area > 0.9 or edges >= 3:                  # fills the frame: a close-up
        return 0.05, b
    size = min(1.0, area / 0.45)                  # big enough bike = 1
    return round(b[4] * size * (1 - 0.3 * edges), 3), b
