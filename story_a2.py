#!/usr/bin/env python3
"""Draft selling designs for the VELTOR stories (group «Сторисы»).
Black background with a light glow in the middle (white or red, about a third of the
background), VELTOR wordmark top-left, Montserrat / Unbounded, 3-4 photos.
The running format (make_story.py) is not changed until a variant is chosen.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import make_story as ms
import story_b as sb
import features

W, H = ms.W, ms.H
FD = Path(__file__).resolve().parent / "fonts"
M2, M3, M5, M6, M7 = (str(FD / f"Montserrat-{w}.ttf") for w in (200, 300, 500, 600, 700))
U3 = str(FD / "Unbounded-300.ttf")
GLOWS = {"white": (246, 246, 244), "red": (196, 18, 32)}
WHITE = (255, 255, 255)
SOFT = (200, 200, 204)
L, R = 64, W - 64
CTA = "Узнать подробности"


def F(path, size):
    return ImageFont.truetype(path, size)


def tw(text, font, tracking=0):
    return ms.text_width(text, font) + tracking * max(0, len(text) - 1)


def text(c, xy, s, font, fill, tracking=0, anchor_right=False, center=False):
    """Text with letter spacing (tracking in px)."""
    dr = ImageDraw.Draw(c)
    x, y = xy
    width = tw(s, font, tracking)
    if anchor_right:
        x -= width
    if center:
        x = (W - width) // 2
    if not tracking:
        dr.text((x, y), s, font=font, fill=fill); return x + width
    for ch in s:
        dr.text((x, y), ch, font=font, fill=fill)
        x += ms.text_width(ch, font) + tracking
    return x - tracking


def fit(s, path, size, max_w, tracking=0, min_size=24):
    f = F(path, size)
    while tw(s, f, tracking) > max_w and size > min_size:
        size -= 2; f = F(path, size)
    return f


# ---------------------------------------------------------------- backgrounds
def background(glow, shape="band", center=0.5, share=0.32):
    """Black with a soft glow; `share` ≈ part of the background lighter than half-way."""
    g = np.array(GLOWS[glow], dtype=np.float32)
    ys = (np.arange(H, dtype=np.float32) / H)[:, None]
    xs = (np.arange(W, dtype=np.float32) / W)[None, :]
    if shape == "band":
        d = np.abs(ys - center) / (share / 2) + 0 * xs          # 1.0 at the half-way line
    else:                                                      # ellipse, wider than tall
        a = share * 1.15
        d = np.sqrt(((xs - 0.5) / (a * 1.25)) ** 2 + ((ys - center) / (a * 0.62)) ** 2)
    u = np.clip(d / 2, 0, 1)
    k = 1 - u * u * (3 - 2 * u)                               # 1 centre, 0.5 at d == 1, 0 at d >= 2
    img = (k[..., None] * g[None, None, :]).astype(np.uint8)
    return Image.fromarray(img, "RGB"), float((k > 0.5).mean())


def light_share(glow, shape, center=0.5, share=0.32):
    return background(glow, shape, center, share)[1]


# ---------------------------------------------------------------- pieces
def wordmark(c, y=196):
    f = F(U3, 40)
    x = text(c, (L, y), "VELTOR", f, WHITE, tracking=14)
    return x


def corner_tag(c, s="ИЗ ЮЖНОЙ КОРЕИ", y=206):
    text(c, (R, y), s, F(M5, 24), SOFT, tracking=5, anchor_right=True)


def title(c, d, y, center=False, size=78, col=WHITE, sub=SOFT):
    brand, model = ms.split_title(d["title"])
    fb = fit(brand.upper(), M3, 34, R - L, tracking=10)
    text(c, (L, y), brand.upper(), fb, sub, tracking=10, center=center)
    fm = fit(model.upper(), M7, size, R - L)
    text(c, (L, y + 50), model.upper(), fm, col, center=center)
    return y + 50 + int(fm.size * 1.12)


def specs(c, d, y, center=False, col=WHITE, sub=SOFT):
    items = [("ГОД", d["year"]), ("ПРОБЕГ", sb.mileage_text(d["mileage"]))]
    fl, fv = F(M5, 24), F(M6, 44)
    widths = [max(tw(a, fl, 4), tw(b, fv)) for a, b in items]
    gap = 90
    x = (W - sum(widths) - gap) // 2 if center else L
    dr = ImageDraw.Draw(c)
    for k, ((a, b), w) in enumerate(zip(items, widths)):
        text(c, (x, y), a, fl, sub, tracking=4)
        text(c, (x, y + 36), b, fv, col)
        if k == 0:
            dr.line([(x + w + gap // 2, y + 6), (x + w + gap // 2, y + 86)], fill=(90, 90, 96), width=2)
        x += w + gap
    return y + 96


def fill_row(items, max_w, sizes=(28, 27, 26, 25, 24, 23, 22), pad=22, gap=12, need=3):
    """Pick selling points (priority order) so that at least `need` fit on ONE line,
    using the largest font that allows it; skipped long ones make room for shorter ones."""
    best = None
    for size in sizes:
        f = F(M5, size); used, pick = 0, []
        for s in items:
            w = tw(s, f) + 2 * pad
            if used + w + (gap if pick else 0) <= max_w:
                used += w + (gap if pick else 0); pick.append((s, w))
        if len(pick) >= min(need, len(items)):
            return f, pick, used
        best = best or (f, pick, used)
    return best


def facts(c, d, y, center=False, col=WHITE, line=(110, 110, 116), h=58, gap=12):
    """One full-width row of outlined chips: at least 3 selling points, never a second line."""
    items = list(d.get("facts") or [])
    for extra in ("Из Южной Кореи", "Цена под ключ"):
        if len(items) < 3 and extra not in items:
            items.append(extra)
    f, pick, used = fill_row(items, R - L, gap=gap)
    extra = (R - L - used) / max(1, len(pick))             # stretch chips to fill the line
    x = float(L)
    dr = ImageDraw.Draw(c)
    for s, w in pick:
        w2 = w + extra
        dr.rounded_rectangle([round(x), y, round(x + w2), y + h], radius=h // 2, outline=line, width=2)
        dr.text((round(x + (w2 - tw(s, f)) / 2), y + (h - f.size) // 2 - 2), s, font=f, fill=col)
        x += w2 + gap
    return y + h


def price(c, d, y, center=False, col=WHITE, sub=SOFT, size=96):
    text(c, (L, y), "ЦЕНА ПОД КЛЮЧ", F(M5, 26), sub, tracking=6, center=center)
    s = f"{d['price']} ₽"
    f = fit(s, M6, size, R - L)
    text(c, (L, y + 40), s, f, col, center=center)
    return y + 40 + int(f.size * 1.18)


def cta(c, glow, y, h=104, fill=None, color=None):
    fill = fill or ((246, 246, 244) if glow == "white" else GLOWS["red"])
    color = color or ((14, 14, 16) if glow == "white" else WHITE)
    sb._rr(c, (L, y, R, y + h), h // 2, fill)
    f = F(M6, 38); aw = 38
    w = tw(CTA, f, 2) + 22 + aw
    x = (W - w) // 2
    text(c, (x, y + (h - 38) // 2 - 6), CTA, f, color, tracking=2)
    sb._put_icon(c, "arrow", x + w - aw, y + (h - aw) // 2, aw, color)
    return y + h


def thumbs(c, paths, y, h, r=22, x0=L, x1=R, gap=14):
    n = len(paths); w = (x1 - x0 - gap * (n - 1)) // n
    for k, p in enumerate(paths):
        sb._pic(c, p, (x0 + k * (w + gap), y, x0 + k * (w + gap) + w, y + h), r)
    return y + h


def feather_photo(c, path, box, fade=140):
    """Edge-to-edge photo whose top and bottom dissolve into the background."""
    x0, y0, x1, y1 = box
    p = sb._photo(path, x1 - x0, y1 - y0)
    a = np.ones((y1 - y0, x1 - x0), np.float32)
    ramp = np.linspace(0, 1, fade, dtype=np.float32); ramp = ramp * ramp * (3 - 2 * ramp)
    a[:fade] *= ramp[:, None]; a[-fade:] *= ramp[::-1, None]
    c.paste(p, (x0, y0), Image.fromarray((a * 255).astype(np.uint8), "L"))


# ---------------------------------------------------------------- variants
def a1_showcase(d, glow):
    c, _ = background(glow, "band", center=0.47)
    wordmark(c); corner_tag(c)
    y = title(c, d, 300)
    ph = sb._gallery(d, 4)
    sb._pic(c, ph[0], (L, y + 24, R, y + 584), 30)
    y = thumbs(c, ph[1:4], y + 600, 190)
    y = specs(c, d, y + 40)
    y = facts(c, d, y + 22)
    y = price(c, d, y + 34, size=88)
    cta(c, glow, y + 18)
    return c


def a2_grid(d, glow):
    c, _ = background(glow, "band", center=0.46)
    wordmark(c); corner_tag(c)
    y = title(c, d, 300)
    ph = sb._gallery(d, 4)
    gw = (R - L - 14) // 2; gh = 340
    for k in range(4):
        x = L + (k % 2) * (gw + 14); yy = y + 26 + (k // 2) * (gh + 14)
        sb._pic(c, ph[k], (x, yy, x + gw, yy + gh), 24)
    y += 26 + 2 * gh + 14
    y = specs(c, d, y + 40)
    y = facts(c, d, y + 22)
    y = price(c, d, y + 34, size=88)
    cta(c, glow, y + 18)
    return c


def a3_column(d, glow):
    """Chosen VELTOR format: tall main photo, up to three photos in a column on the right."""
    c, _ = background(glow, "ellipse", center=0.45, share=0.33)
    wordmark(c); corner_tag(c)
    y = title(c, d, 300)
    ph = [p for p in (d.get("photos") or [d["main"], d.get("second")]) if p][:4]
    top = y + 26; hh = 780; bw = 620 if len(ph) > 1 else R - L
    sb._pic(c, ph[0], (L, top, L + bw, top + hh), 28)
    side = ph[1:]
    if side:
        sh = (hh - 14 * (len(side) - 1)) // len(side)
        for k, p in enumerate(side):
            sb._pic(c, p, (L + bw + 14, top + k * (sh + 14), R, top + k * (sh + 14) + sh), 22)
    y = top + hh
    y = specs(c, d, y + 40)
    y = facts(c, d, y + 22)
    y = price(c, d, y + 34, size=88)
    cta(c, glow, y + 18)
    return c


def a4_price_center(d, glow):
    """Price sits in the light glow in the middle, photos above and below."""
    c, _ = background(glow, "band", center=0.53, share=0.30)
    ink = (14, 14, 16) if glow == "white" else WHITE
    sub = (90, 90, 96) if glow == "white" else (255, 214, 218)
    wordmark(c); corner_tag(c)
    y = title(c, d, 300)
    ph = sb._gallery(d, 4)
    sb._pic(c, ph[0], (L, y + 24, R, y + 520), 30)
    y += 520 + 50
    text(c, (L, y), "ЦЕНА ПОД КЛЮЧ", F(M5, 26), sub, tracking=6, center=True)
    s = f"{d['price']} ₽"
    f = fit(s, M7, 128, R - L)
    text(c, (L, y + 40), s, f, ink, center=True)
    y += 40 + int(f.size * 1.2) + 10
    y = thumbs(c, ph[1:4], y, 200)
    y = specs(c, d, y + 40, center=True)
    cta(c, glow, y + 40)
    return c


def a5_cinema(d, glow):
    """Edge-to-edge main photo dissolving into the background, thumbnails underneath."""
    c, _ = background(glow, "ellipse", center=0.46, share=0.32)
    wordmark(c); corner_tag(c)
    y = title(c, d, 300, center=True)
    ph = sb._gallery(d, 4)
    feather_photo(c, ph[0], (0, y - 10, W, y + 660), fade=140)
    y = thumbs(c, ph[1:4], y + 610, 170)
    y = specs(c, d, y + 40, center=True)
    y = facts(c, d, y + 22, center=True)
    y = price(c, d, y + 34, center=True, size=88)
    cta(c, glow, y + 18)
    return c


VARIANTS = {"1_showcase": a1_showcase, "2_grid": a2_grid, "3_column": a3_column,
            "4_price_center": a4_price_center, "5_cinema": a5_cinema}


def build_a2(variant, glow, photos, title_, year, mileage, price_, out, description=""):
    d = {"main": photos[0], "second": photos[1] if len(photos) > 1 else None, "photos": photos,
         "title": title_, "year": year, "mileage": mileage, "price": price_,
         "facts": features.extract(description)}
    img = VARIANTS[variant](d, glow)
    img.save(out, quality=95, subsampling=0)
    return out


# ---------------------------------------------------- whole bike on the main photo
def main_score(path):
    """Main photo rule: the bike from the SIDE (or the view showing the most of it), whole,
    not a close-up. Front/rear views have a narrow box (width/height < ~0.9) and score low;
    close-ups fill the frame or touch its edges and score lowest."""
    import detect
    boxes = detect.motorcycle_boxes(path)
    if not boxes:
        return 0.0, None
    iw, ih = Image.open(path).size
    b = max(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]) * b[4])
    area = (b[2] - b[0]) * (b[3] - b[1])
    aspect = (b[2] - b[0]) * iw / max(1e-6, (b[3] - b[1]) * ih)
    cut = sum([b[0] < 0.01, b[1] < 0.01, b[2] > 0.99, b[3] > 0.99])
    side = min(1.0, max(0.0, (aspect - 0.75) / (1.45 - 0.75)))   # 0 = front/rear, 1 = side
    size = min(1.0, area / 0.25)
    close = 0.08 if area >= 0.9 else 1.0                          # bike fills the frame: close-up
    return b[4] * size * (0.12 + 0.88 * side) * (0.6 ** cut) * close, b


def order_for_main(photos):
    """Main photo = side view / most of the bike visible (an earlier one wins a near tie)."""
    scored = [(p, main_score(p)[0]) for p in photos]
    best = scored[0]
    for sc in scored[1:]:
        if sc[1] > best[1] + 0.03:
            best = sc
    return [best[0]] + [p for p, _ in scored if p != best[0]]


def photo_whole(path, w, h_min, h_max, margin=0.06):
    """Crop around the WHOLE motorcycle (never cut it): returns (image, height).
    The card gets taller (up to h_max) when the bike needs it; if the photo still can't
    hold the bike with the margin, the missing strip is filled with a blurred copy."""
    from PIL import ImageFilter
    img = ms.prepare_photo(path)
    iw, ih = img.size
    box = ms._bike_box(path)
    if not box:
        p = sb._photo(path, w, h_min, focus=False); return p, h_min
    bx0, by0, bx1, by1 = box[0] * iw, box[1] * ih, box[2] * iw, box[3] * ih
    mx, my = (bx1 - bx0) * margin, (by1 - by0) * margin
    # margin only where the photo has it: a bike touching the frame edge gets no blurred strip
    bx0, bx1, by0, by1 = max(0, bx0 - mx), min(iw, bx1 + mx), max(0, by0 - my), min(ih, by1 + my)
    bw, bh = bx1 - bx0, by1 - by0
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    for h in range(h_min, h_max + 1, 10):
        a = w / h
        rw = max(bw, bh * a); rh = rw / a
        if rw <= iw and rh <= ih:
            break
    a = w / h
    rw = max(bw, bh * a); rh = rw / a
    if rw <= iw and rh <= ih:
        x = min(max(0, cx - rw / 2), iw - rw); y = min(max(0, cy - rh / 2), ih - rh)
        return img.crop((round(x), round(y), round(x + rw), round(y + rh))).resize((w, h), Image.LANCZOS), h
    # the region is larger than the photo: blurred fill around the real picture
    rw, rh = round(rw), round(rh)
    s = max(rw / iw, rh / ih)
    fill = img.resize((round(iw * s), round(ih * s)), Image.LANCZOS).filter(ImageFilter.GaussianBlur(28))
    fill = fill.crop(((fill.width - rw) // 2, (fill.height - rh) // 2, (fill.width - rw) // 2 + rw,
                      (fill.height - rh) // 2 + rh))
    x = round(min(max(cx - rw / 2, iw - rw), 0)) if rw > iw else round(min(max(0, cx - rw / 2), iw - rw))
    y = round(min(max(cy - rh / 2, ih - rh), 0)) if rh > ih else round(min(max(0, cy - rh / 2), ih - rh))
    part = img.crop((max(0, x), max(0, y), min(iw, x + rw), min(ih, y + rh)))
    fill.paste(part, (max(0, -x), max(0, -y)))
    return fill.resize((w, h), Image.LANCZOS), h


def main_card(c, path, y, h_min, h_max, r=30):
    p, h = photo_whole(path, R - L, h_min, h_max)
    c.paste(p, (L, y), sb._round(p, r))
    return y + h


# ---------------------------------------------------- showcase without the button
HANDLE = "@VELTOR_KOR"


def _showcase_top(d, glow, h_min, h_max, thumb_h=190):
    c, _ = background(glow, "band", center=0.47)
    wordmark(c); corner_tag(c)
    y = title(c, d, 300)
    ph = order_for_main([p for p in (d.get("photos") or [d["main"]]) if p][:4])
    y = main_card(c, ph[0], y + 24, h_min, h_max)
    if len(ph) > 1:
        y = thumbs(c, ph[1:4], y + 16, thumb_h)
    y = specs(c, d, y + 40)
    if d.get("show_facts"):
        y = facts(c, d, y + 22)
    return c, y


def s1_clean(d, glow):
    """No button: bigger price, the photo gets the space."""
    c, y = _showcase_top(d, glow, 620, 700)
    price(c, d, y + 40, size=112)
    return c


def s2_contact(d, glow):
    """Instead of the button: an outlined line with the manager's contact."""
    c, y = _showcase_top(d, glow, 580, 660)
    y = price(c, d, y + 34, size=96)
    h = 92
    dr = ImageDraw.Draw(c)
    dr.rounded_rectangle([L, y + 18, R, y + 18 + h], radius=h // 2, outline=(150, 150, 156), width=2)
    a, b = "НАПИСАТЬ МЕНЕДЖЕРУ", HANDLE
    fa, fb = F(M5, 26), F(M6, 36)
    wa, wb = tw(a, fa, 5), tw(b, fb)
    x = (W - wa - 28 - wb) // 2
    text(c, (x, y + 18 + (h - 26) // 2 - 4), a, fa, SOFT, tracking=5)
    text(c, (x + wa + 28, y + 18 + (h - 36) // 2 - 6), b, fb, WHITE)
    return c


def s3_price_pill(d, glow):
    """The light pill now holds the price itself."""
    c, y = _showcase_top(d, glow, 600, 680)
    y += 40
    text(c, (L, y), "ЦЕНА ПОД КЛЮЧ", F(M5, 26), SOFT, tracking=6)
    h = 132
    sb._rr(c, (L, y + 44, R, y + 44 + h), h // 2, (246, 246, 244) if glow == "white" else GLOWS["red"])
    s = f"{d['price']} ₽"
    f = fit(s, M7, 92, R - L - 80)
    text(c, (L, y + 44 + (h - f.size) // 2 - 10), s, f, (14, 14, 16) if glow == "white" else WHITE, center=True)
    return c


def s4_slogan(d, glow):
    """Price, then a thin rule and a quiet line from VELTOR's own posts."""
    c, y = _showcase_top(d, glow, 600, 680)
    y = price(c, d, y + 34, size=104)
    dr = ImageDraw.Draw(c)
    dr.line([(L, y + 22), (R, y + 22)], fill=(70, 70, 76), width=2)
    s = "ОРГАНИЗУЕМ ДОСТАВКУ ПОД КЛЮЧ"
    text(c, (L, y + 50), s, fit(s, M5, 28, R - L, tracking=7), SOFT, tracking=7)
    return c


VARIANTS.update({"s1_clean": s1_clean, "s2_contact": s2_contact,
                 "s3_price_pill": s3_price_pill, "s4_slogan": s4_slogan})
