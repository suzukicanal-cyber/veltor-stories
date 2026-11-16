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


def whole(c, path, box, r=0, grow=120):
    """Whole bike in the box; the box may grow by up to `grow` px in height when the bike
    needs it (instead of blurred side strips). Returns the bottom y."""
    x0, y0, x1, y1 = box
    p, h = a2.photo_whole(path, x1 - x0, y1 - y0, y1 - y0 + grow)
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


VARIANTS = {"m1_magazine": v1_magazine, "m2_red": v2_red, "m3_split": v3_split,
            "m4_card": v4_card, "m5_center": v5_center}


def build_a3(variant, photos_, title_, year, mileage, price_, out):
    d = {"main": photos_[0], "photos": photos_, "title": title_, "year": year,
         "mileage": mileage, "price": price_}
    VARIANTS[variant](d).save(out, quality=95, subsampling=0)
    return out
