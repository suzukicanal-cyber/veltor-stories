#!/usr/bin/env python3
"""New VELTOR story directions for «Сторисы» (16.11.2026 draft, not active until chosen).

All variants keep the rules agreed so far: the main photo shows the WHOLE bike (side view
preferred, never rear or close-up), no features row, no button, VELTOR wordmark top-left,
model / year / mileage / price under the key, Montserrat + Unbounded.
"""
from PIL import Image, ImageDraw

import make_story as ms
import story_a2 as a2
import story_b as sb
from story_a2 import F, M3, M5, M6, M7, U3, text, tw, fit

W, H = 1080, 1920
L, R = 64, W - 64
INK = (18, 18, 20)
GREY = (120, 120, 126)
RED = (200, 22, 36)


def wordmark(c, x, y, col, size=40, center=False):
    text(c, (x, y), "VELTOR", F(U3, size), col, tracking=14, center=center)


def tag(c, y, col, s="ИЗ ЮЖНОЙ КОРЕИ"):
    text(c, (R, y + 10), s, F(M5, 22), col, tracking=5, anchor_right=True)


def photos(d):
    ph = [p for p in (d.get("photos") or [d["main"]]) if p][:4]
    ph = a2.order_for_main(ph)
    while len(ph) < 4:
        ph.append(ph[len(ph) % max(1, len(ph))])
    return ph


def _fits(path, w, h, margin=0.06):
    """True if the whole bike fits a w x h crop of the photo without blurred filling."""
    img = ms.prepare_photo(path); iw, ih = img.size
    box = ms._bike_box(path)
    if not box:
        return True
    bx0, by0, bx1, by1 = box[0] * iw, box[1] * ih, box[2] * iw, box[3] * ih
    mx, my = (bx1 - bx0) * margin, (by1 - by0) * margin
    bw = min(iw, bx1 + mx) - max(0, bx0 - mx); bh = min(ih, by1 + my) - max(0, by0 - my)
    a = w / h; rw = max(bw, bh * a); rh = rw / a
    return rw <= iw + 0.5 and rh <= ih + 0.5


def best_h(path, w, base, grow=120, shrink=220):
    """The tallest card height near `base` that shows the whole bike WITHOUT blur
    (taller for upright bikes, shorter for long ones); `base` if none fits."""
    for h in range(base + grow, base - shrink - 1, -10):
        if _fits(path, w, h):
            return h
    return base


def whole(c, path, box, r=0, grow=120, shrink=220):
    """Whole bike in the box; the box height adapts (-shrink..+grow) so that no blurred
    strips are needed. Returns the bottom y."""
    x0, y0, x1, y1 = box
    h0 = best_h(path, x1 - x0, y1 - y0, grow, shrink)
    p, h = a2.photo_whole(path, x1 - x0, h0, h0)
    c.paste(p, (x0, y0), sb._round(p, r) if r else None)
    return y0 + h


def cover(c, path, box, r=0):
    x0, y0, x1, y1 = box
    p = sb._photo(path, x1 - x0, y1 - y0)
    c.paste(p, (x0, y0), sb._round(p, r) if r else None)


def row(c, paths, y, h, x0=L, x1=R, gap=14, r=20):
    n = len(paths); w = (x1 - x0 - gap * (n - 1)) // n
    for k, p in enumerate(paths):
        cover(c, p, (x0 + k * (w + gap), y, x0 + k * (w + gap) + w, y + h), r)
    return y + h


def names(d):
    brand, model = ms.split_title(d["title"])
    return brand.upper(), model.upper()


def specs_line(d):
    return f"{d['year']}   ·   {sb.mileage_text(d['mileage'])}"


def price_s(d):
    return f"{d['price']} ₽"


# ---------------------------------------------------------------- 1. Журнал
def v1_magazine(d):
    """Light editorial: edge-to-edge photo, big black model name, large price, lots of air."""
    c = Image.new("RGB", (W, H), (246, 245, 242))
    wordmark(c, L, 168, INK); tag(c, 168, GREY)
    ph = photos(d)
    yb = whole(c, ph[0], (0, 260, W, 900), grow=110)
    yb = row(c, ph[1:4], yb + 6, 190, x0=0, x1=W, gap=6, r=0)
    brand, model = names(d)
    text(c, (L, yb + 50), brand, fit(brand, M3, 32, R - L, tracking=10), GREY, tracking=10)
    fm = fit(model, M7, 96, R - L)
    text(c, (L, yb + 94), model, fm, INK)
    y = yb + 94 + int(fm.size * 1.15)
    text(c, (L, y + 6), specs_line(d), F(M5, 40), GREY)
    ImageDraw.Draw(c).line([(L, y + 86), (R, y + 86)], fill=(212, 210, 205), width=2)
    text(c, (L, y + 116), "ЦЕНА ПОД КЛЮЧ", F(M5, 24), GREY, tracking=6)
    text(c, (L, y + 150), price_s(d), fit(price_s(d), M7, 112, R - L), INK)
    return c


# ---------------------------------------------------------------- 2. Красный
def v2_red(d):
    """Brand red background, photos in white frames, white type."""
    c = Image.new("RGB", (W, H))
    top, bot = (186, 18, 32), (120, 8, 18)
    dr = ImageDraw.Draw(c)
    for y in range(H):
        t = y / H
        dr.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    wordmark(c, L, 168, (255, 255, 255)); tag(c, 168, (255, 205, 210))
    brand, model = names(d)
    text(c, (L, 262), brand, fit(brand, M3, 32, R - L, tracking=10), (255, 205, 210), tracking=10)
    fm = fit(model, M7, 84, R - L)
    text(c, (L, 304), model, fm, (255, 255, 255))
    y = 304 + int(fm.size * 1.15) + 14
    ph = photos(d)
    p, h = a2.photo_whole(ph[0], R - L, 600, 700)
    sb._rr(c, (L - 10, y - 10, R + 10, y + h + 10), 40, (255, 255, 255))
    c.paste(p, (L, y), sb._round(p, 32))
    y += h + 30
    hw = (R - L - 16) // 2
    th = 250 - max(0, h - 600)
    cover(c, ph[1], (L, y, L + hw, y + th), 26)
    cover(c, ph[2], (L + hw + 16, y, R, y + th), 26)
    y += th + 40
    text(c, (L, y), specs_line(d), F(M6, 42), (255, 255, 255))
    text(c, (L, y + 80), "ЦЕНА ПОД КЛЮЧ", F(M5, 24), (255, 205, 210), tracking=6)
    text(c, (L, y + 114), price_s(d), fit(price_s(d), M7, 104, R - L), (255, 255, 255))
    return c


# ---------------------------------------------------------------- 3. Сплит
def v3_split(d):
    """Graphite top with all the text, light bottom; the main photo bridges the two halves."""
    c = Image.new("RGB", (W, H), (238, 237, 234))
    ImageDraw.Draw(c).rectangle([0, 0, W, 900], fill=(26, 26, 29))
    wordmark(c, L, 168, (255, 255, 255)); tag(c, 168, (150, 150, 156))
    brand, model = names(d)
    text(c, (L, 270), brand, fit(brand, M3, 32, R - L, tracking=10), (150, 150, 156), tracking=10)
    fm = fit(model, M7, 88, R - L)
    text(c, (L, 312), model, fm, (255, 255, 255))
    y = 312 + int(fm.size * 1.15)
    text(c, (L, y + 8), specs_line(d), F(M5, 38), (190, 190, 196))
    text(c, (L, y + 84), "ЦЕНА ПОД КЛЮЧ", F(M5, 24), (150, 150, 156), tracking=6)
    ps = price_s(d)
    pf = fit(ps, M7, 100, R - L - 40)
    text(c, (L, y + 118), ps, pf, (255, 255, 255))
    ImageDraw.Draw(c).rectangle([L, y + 118 + int(pf.size * 1.2), L + 120, y + 124 + int(pf.size * 1.2)], fill=RED)
    ph = photos(d)
    yb = whole(c, ph[0], (L, 760, R, 1340), r=34, grow=100)
    row(c, ph[1:4], yb + 20, 220, r=24)
    return c


# ---------------------------------------------------------------- 4. Карточка
def v4_card(d):
    """Product card: one white card on light grey — photo, three thumbnails, text, price row."""
    c = Image.new("RGB", (W, H), (232, 232, 235))
    x0, x1 = 40, W - 40
    card = Image.new("RGB", (W, H), (255, 255, 255))     # drawn later, height fitted to content
    canvas, c = c, card
    pl, pr = x0 + 36, x1 - 36
    wordmark(c, pl, 196, INK, size=34)
    text(c, (pr, 204), "ИЗ ЮЖНОЙ КОРЕИ", F(M5, 20), GREY, tracking=5, anchor_right=True)
    ph = photos(d)
    yb = whole(c, ph[0], (pl, 270, pr, 900), r=28, grow=100)
    yb = row(c, ph[1:4], yb + 14, 230, x0=pl, x1=pr, gap=12, r=20)
    brand, model = names(d)
    text(c, (pl, yb + 46), brand, fit(brand, M3, 30, pr - pl, tracking=10), GREY, tracking=10)
    fm = fit(model, M7, 80, pr - pl)
    text(c, (pl, yb + 86), model, fm, INK)
    y = yb + 86 + int(fm.size * 1.2) + 10
    fx = pl
    for lab, val in (("ГОД", d["year"]), ("ПРОБЕГ", sb.mileage_text(d["mileage"]))):
        f = F(M6, 34); w = tw(val, f) + tw(lab, F(M5, 20), 4) + 70
        sb._rr(c, (fx, y, fx + w, y + 72), 36, (243, 243, 245))
        text(c, (fx + 26, y + 26), lab, F(M5, 20), GREY, tracking=4)
        text(c, (fx + 26 + tw(lab, F(M5, 20), 4) + 18, y + 16), val, f, INK)
        fx += w + 14
    y += 110
    ImageDraw.Draw(c).line([(pl, y), (pr, y)], fill=(232, 232, 235), width=2)
    text(c, (pl, y + 40), "Цена под ключ", F(M5, 32), GREY)
    ps = price_s(d)
    text(c, (pr, y + 24), ps, fit(ps, M7, 72, (pr - pl) // 2 + 120), INK, anchor_right=True)
    bottom = y + 130
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).rounded_rectangle([x0, 150, x1, bottom], radius=44, fill=255)
    canvas.paste(card, (0, 0), m)
    return canvas


# ---------------------------------------------------------------- 5. Центр
def v5_center(d):
    """Calm charcoal (no glow), everything centred: model, photos, specs, price with a red rule."""
    c = Image.new("RGB", (W, H), (20, 20, 22))
    wordmark(c, 0, 168, (255, 255, 255), center=True)
    brand, model = names(d)
    text(c, (0, 262), brand, fit(brand, M3, 30, R - L, tracking=10), (150, 150, 156), tracking=10, center=True)
    fm = fit(model, M7, 80, R - L)
    text(c, (0, 302), model, fm, (255, 255, 255), center=True)
    y = 302 + int(fm.size * 1.15) + 16
    ph = photos(d)
    yb = whole(c, ph[0], (L, y, R, y + 600), r=30, grow=100)
    y = row(c, ph[1:4], yb + 14, 200 - max(0, yb - y - 600), r=22)
    sl = specs_line(d)
    text(c, (0, y + 44), sl, F(M5, 38), (200, 200, 206), center=True)
    text(c, (0, y + 124), "ЦЕНА ПОД КЛЮЧ", F(M5, 24), (150, 150, 156), tracking=6, center=True)
    ps = price_s(d)
    pf = fit(ps, M7, 104, R - L)
    text(c, (0, y + 160), ps, pf, (255, 255, 255), center=True)
    yy = y + 160 + int(pf.size * 1.25)
    ImageDraw.Draw(c).rectangle([W // 2 - 60, yy, W // 2 + 60, yy + 6], fill=RED)
    return c



# ------------------------------------------------ more in the spirit of 1, 3 and 4
def v1b_magazine_center(d):
    """Like 1: light, but the photo has margins and rounded corners, everything centred."""
    c = Image.new("RGB", (W, H), (246, 245, 242))
    wordmark(c, 0, 168, INK, center=True)
    ph = photos(d)
    yb = whole(c, ph[0], (L, 250, R, 930), r=32, grow=80)
    yb = row(c, ph[1:4], yb + 14, 240 - max(0, yb - 930), r=22)
    brand, model = names(d)
    text(c, (0, yb + 54), brand, fit(brand, M3, 30, R - L, tracking=10), GREY, tracking=10, center=True)
    fm = fit(model, M7, 90, R - L)
    text(c, (0, yb + 96), model, fm, INK, center=True)
    y = yb + 96 + int(fm.size * 1.15)
    text(c, (0, y + 6), specs_line(d), F(M5, 38), GREY, center=True)
    text(c, (0, y + 90), "ЦЕНА ПОД КЛЮЧ", F(M5, 24), GREY, tracking=6, center=True)
    ps = price_s(d); pf = fit(ps, M7, 108, R - L)
    text(c, (0, y + 124), ps, pf, INK, center=True)
    yy = y + 124 + int(pf.size * 1.25)
    ImageDraw.Draw(c).rectangle([W // 2 - 60, yy, W // 2 + 60, yy + 6], fill=RED)
    return c


def v1c_magazine_top(d):
    """Like 1, flipped: model and price at the top on light, the photos fill the lower part."""
    c = Image.new("RGB", (W, H), (246, 245, 242))
    wordmark(c, L, 168, INK); tag(c, 168, GREY)
    brand, model = names(d)
    text(c, (L, 262), brand, fit(brand, M3, 32, R - L, tracking=10), GREY, tracking=10)
    fm = fit(model, M7, 92, R - L)
    text(c, (L, 304), model, fm, INK)
    y = 304 + int(fm.size * 1.15)
    text(c, (L, y + 6), specs_line(d), F(M5, 38), GREY)
    ps = price_s(d); pf = fit(ps, M7, 96, R - L)
    text(c, (L, y + 74), ps, pf, INK)
    text(c, (L + tw(ps, pf) + 24, y + 74 + pf.size - 34), "под ключ", F(M5, 28), GREY)
    y += 74 + int(pf.size * 1.3) + 20
    ph = photos(d)
    yb = whole(c, ph[0], (0, y, W, y + 820), grow=60)
    row(c, ph[1:4], yb + 6, min(300, 1790 - yb - 6), x0=0, x1=W, gap=6, r=0)
    return c


def v3b_split_reverse(d):
    """Like 3, reversed: light top with the photos, graphite bottom with all the text."""
    c = Image.new("RGB", (W, H), (238, 237, 234))
    ImageDraw.Draw(c).rectangle([0, 1100, W, H], fill=(26, 26, 29))
    wordmark(c, L, 168, INK); tag(c, 168, GREY)
    ph = photos(d)
    yb = row(c, ph[1:4], 250, 200, r=22)
    yb = whole(c, ph[0], (L, yb + 16, R, yb + 16 + 620), r=34, grow=60)
    y = max(1100, yb) + 50
    brand, model = names(d)
    text(c, (L, y), brand, fit(brand, M3, 30, R - L, tracking=10), (150, 150, 156), tracking=10)
    fm = fit(model, M7, 84, R - L)
    text(c, (L, y + 40), model, fm, (255, 255, 255))
    y += 40 + int(fm.size * 1.15)
    text(c, (L, y + 6), specs_line(d), F(M5, 38), (190, 190, 196))
    ps = price_s(d); pf = fit(ps, M7, 96, R - L)
    text(c, (L, y + 70), ps, pf, (255, 255, 255))
    ImageDraw.Draw(c).rectangle([L, y + 70 + int(pf.size * 1.22), L + 120, y + 76 + int(pf.size * 1.22)], fill=RED)
    return c


def v3c_split_two(d):
    """Like 3, but two big photos instead of three small ones under the main photo."""
    c = Image.new("RGB", (W, H), (238, 237, 234))
    ImageDraw.Draw(c).rectangle([0, 0, W, 860], fill=(26, 26, 29))
    wordmark(c, L, 168, (255, 255, 255)); tag(c, 168, (150, 150, 156))
    brand, model = names(d)
    text(c, (L, 266), brand, fit(brand, M3, 30, R - L, tracking=10), (150, 150, 156), tracking=10)
    fm = fit(model, M7, 86, R - L)
    text(c, (L, 306), model, fm, (255, 255, 255))
    y = 306 + int(fm.size * 1.15)
    text(c, (L, y + 6), specs_line(d), F(M5, 36), (190, 190, 196))
    ps = price_s(d); pf = fit(ps, M7, 92, R - L)
    text(c, (L, y + 66), ps, pf, (255, 255, 255))
    text(c, (L + tw(ps, pf) + 22, y + 66 + pf.size - 32), "под ключ", F(M5, 26), (150, 150, 156))
    ph = photos(d)
    yb = whole(c, ph[0], (L, 720, R, 1380), r=34, grow=60)
    hw = (R - L - 16) // 2; th = min(360, 1780 - yb - 18)
    cover(c, ph[1], (L, yb + 18, L + hw, yb + 18 + th), 26)
    cover(c, ph[2], (L + hw + 16, yb + 18, R, yb + 18 + th), 26)
    return c


def _card(d, page_bg, head_dark=False):
    c = Image.new("RGB", (W, H), page_bg)
    card = Image.new("RGB", (W, H), (255, 255, 255))
    x0, x1 = 40, W - 40; pl, pr = x0 + 36, x1 - 36
    brand, model = names(d)
    ps = price_s(d)
    if head_dark:
        ImageDraw.Draw(card).rectangle([x0, 150, x1, 470], fill=(26, 26, 29))
        wordmark(card, pl, 196, (255, 255, 255), size=34)
        text(card, (pr, 204), "ИЗ ЮЖНОЙ КОРЕИ", F(M5, 20), (150, 150, 156), tracking=5, anchor_right=True)
        text(card, (pl, 282), brand, fit(brand, M3, 28, pr - pl, tracking=10), (150, 150, 156), tracking=10)
        fm = fit(model, M7, 74, pr - pl)
        text(card, (pl, 320), model, fm, (255, 255, 255))
        y0 = 500
    else:
        wordmark(card, pl, 196, INK, size=34)
        text(card, (pr, 204), "ИЗ ЮЖНОЙ КОРЕИ", F(M5, 20), GREY, tracking=5, anchor_right=True)
        y0 = 270
    ph = photos(d)
    yb = whole(card, ph[0], (pl, y0, pr, y0 + (640 if head_dark else 700)), r=28, grow=60)
    yb = row(card, ph[1:4], yb + 14, 250, x0=pl, x1=pr, gap=12, r=20)
    y = yb + 40
    if not head_dark:
        text(card, (pl, y), brand, fit(brand, M3, 30, pr - pl, tracking=10), GREY, tracking=10)
        fm = fit(model, M7, 78, pr - pl)
        text(card, (pl, y + 40), model, fm, INK)
        y += 40 + int(fm.size * 1.2) + 10
    fx = pl
    for lab, val in (("ГОД", d["year"]), ("ПРОБЕГ", sb.mileage_text(d["mileage"]))):
        f = F(M6, 34); w = tw(val, f) + tw(lab, F(M5, 20), 4) + 70
        sb._rr(card, (fx, y, fx + w, y + 72), 36, (243, 243, 245))
        text(card, (fx + 26, y + 26), lab, F(M5, 20), GREY, tracking=4)
        text(card, (fx + 26 + tw(lab, F(M5, 20), 4) + 18, y + 16), val, f, INK)
        fx += w + 14
    y += 110
    ImageDraw.Draw(card).line([(pl, y), (pr, y)], fill=(232, 232, 235), width=2)
    text(card, (pl, y + 40), "Цена под ключ", F(M5, 32), GREY)
    text(card, (pr, y + 24), ps, fit(ps, M7, 72, (pr - pl) // 2 + 120), INK, anchor_right=True)
    bottom = y + 130
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).rounded_rectangle([x0, 150, x1, bottom], radius=44, fill=255)
    c.paste(card, (0, 0), m)
    return c


def v4b_card_dark(d):
    """Like 4: the same white product card, on a dark page."""
    return _card(d, (22, 22, 24))


def v4c_card_header(d):
    """Like 4: white card with a dark header holding the wordmark and the model."""
    return _card(d, (232, 232, 235), head_dark=True)


VARIANTS = {"m1_magazine": v1_magazine, "m2_red": v2_red, "m3_split": v3_split,
            "m4_card": v4_card, "m5_center": v5_center,
            "m1b_magazine_center": v1b_magazine_center, "m1c_magazine_top": v1c_magazine_top,
            "m3b_split_reverse": v3b_split_reverse, "m3c_split_two": v3c_split_two,
            "m4b_card_dark": v4b_card_dark, "m4c_card_header": v4c_card_header}


def build_a3(variant, photos_, title_, year, mileage, price_, out):
    d = {"main": photos_[0], "photos": photos_, "title": title_, "year": year,
         "mileage": mileage, "price": price_}
    VARIANTS[variant](d).save(out, quality=95, subsampling=0)
    return out
