#!/usr/bin/env python3
"""Format B stories (second channel): same Moto posts and the same 5 lines,
price + 50 000 ₽, delivered to a separate chat. Several design variants;
the chosen one is set in config.json ("format_b": {"variant": "..."}).
Format A (make_story.py) is not touched.
"""
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import make_story as ms

W, H = ms.W, ms.H
PRICE_ADD = 50_000
F_BOLD = ms.F_VALUE
F_REG = ms.F_LABEL
F_ITALIC = ms.F_MODEL
F_BRAND = ms.F_BRAND
ACCENT = (214, 36, 44)


def price_plus(price, add=PRICE_ADD):
    n = int(re.sub(r"\D", "", price)) + add
    return f"{n:,}".replace(",", " ")


def mileage_text(m):
    return f"{m} km" if m[:1].isdigit() else m.upper()


def _font(path, size):
    return ImageFont.truetype(path, size)


def _fit(text, path, size, max_w, min_size=24):
    f = _font(path, size)
    while ms.text_width(text, f) > max_w and size > min_size:
        size -= 2; f = _font(path, size)
    return f


def _photo(path, w, h, focus=True):
    """Photo cover-cropped to w x h around the bike."""
    img = ms.prepare_photo(path)
    s = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    box = ms._bike_box(path) if focus else None
    cx = ((box[0] + box[2]) / 2 * img.width) if box else img.width / 2
    cy = ((box[1] + box[3]) / 2 * img.height) if box else img.height / 2
    x = int(min(max(0, cx - w / 2), img.width - w)); y = int(min(max(0, cy - h / 2), img.height - h))
    return img.crop((x, y, x + w, y + h))


def _round(img, r):
    m = Image.new("L", (img.width * 3, img.height * 3), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, m.width - 1, m.height - 1], radius=r * 3, fill=255)
    return m.resize(img.size, Image.LANCZOS)


def _vgrad(canvas, y0, y1, top_alpha, bottom_alpha, color=(0, 0, 0)):
    a = Image.new("L", (W, H), 0); d = ImageDraw.Draw(a)
    for y in range(max(0, y0), min(H, y1)):
        t = (y - y0) / max(1, y1 - y0)
        d.line([(0, y), (W, y)], fill=int(255 * (top_alpha + (bottom_alpha - top_alpha) * ms.smoothstep(t))))
    return Image.composite(Image.new("RGB", (W, H), color), canvas, a)


def _split(title):
    return ms.split_title(title)


def _icon(canvas, icon4x, x, y, size, color=(255, 255, 255)):
    canvas.paste(color, (x, y, x + size, y + size), icon4x.resize((size, size), Image.LANCZOS))


LOGO = Path(__file__).resolve().parent / "brand" / "da_motors_dark.png"


def _logo(canvas, right, cy, max_w, width=400):
    """DA Motors logo (dark version for the light design), right-aligned."""
    if not LOGO.exists():
        return
    lg = Image.open(LOGO).convert("RGBA")
    w = int(min(width, max_w))
    lg = lg.resize((w, round(lg.height * w / lg.width)), Image.LANCZOS)
    canvas.paste(lg, (right - lg.width, cy - lg.height // 2), lg)


# ---------------------------------------------------------------- variants
def v1_hero(d):
    """Full-screen hero photo, info at the bottom on a dark gradient, big price."""
    c = _photo(d["main"], W, H)
    c = _vgrad(c, 0, 520, 0.85, 0.0)
    c = _vgrad(c, 1060, H, 0.0, 0.92)
    dr = ImageDraw.Draw(c)
    brand, model = _split(d["title"])
    dr.text((72, 150), brand.upper(), font=_fit(brand.upper(), F_BRAND, 74, W - 144), fill="white")
    dr.text((72, 232), model.upper(), font=_fit(model.upper(), F_ITALIC, 64, W - 144), fill="white")
    y = 1290
    for icon, txt in ((ms.icon_calendar(), d["year"]), (ms.icon_speedometer(), mileage_text(d["mileage"]))):
        _icon(c, icon, 72, y, 54)
        dr.text((146, y + 2), txt, font=_font(F_BOLD, 46), fill="white")
        y += 78
    dr.text((72, y + 20), "Цена под ключ", font=_font(F_REG, 38), fill=(220, 220, 220))
    dr.text((72, y + 66), f"{d['price']} ₽", font=_font(F_BOLD, 104), fill="white")
    dr.rectangle([72, y + 200, 72 + 150, y + 208], fill=ACCENT)
    return c


def v2_light(d):
    """Light premium: white background, big rounded photo, dark text, price in an accent pill."""
    c = Image.new("RGB", (W, H), (244, 243, 240))
    dr = ImageDraw.Draw(c)
    brand, model = _split(d["title"])
    dr.text((64, 150), brand.upper(), font=_fit(brand.upper(), F_BRAND, 70, W - 128), fill=(20, 20, 22))
    dr.text((64, 228), model.upper(), font=_fit(model.upper(), F_ITALIC, 60, W - 128), fill=(90, 90, 96))
    p = _photo(d["main"], W - 128, 760)
    c.paste(p, (64, 360), _round(p, 36))
    if d.get("second"):
        p2 = _photo(d["second"], (W - 128 - 24) // 2, 330)
        c.paste(p2, (64, 1144), _round(p2, 28))
    x0 = 64 + (W - 128 + 24) // 2 if d.get("second") else 64
    y = 1150
    for label, val in (("Год", d["year"]), ("Пробег", mileage_text(d["mileage"]))):
        dr.text((x0, y), label, font=_font(F_REG, 34), fill=(110, 110, 116))
        dr.text((x0, y + 40), val, font=_font(F_BOLD, 52), fill=(20, 20, 22))
        y += 140
    pf = _font(F_BOLD, 76)
    txt = f"{d['price']} ₽"
    tw = ms.text_width(txt, pf)
    dr.text((64, 1520), "Цена под ключ с ЭПТС", font=_font(F_REG, 36), fill=(110, 110, 116))
    dr.rounded_rectangle([64, 1570, 64 + tw + 72, 1690], radius=60, fill=ACCENT)
    dr.text((100, 1584), txt, font=pf, fill="white")
    _logo(c, right=W - 64, cy=1630, max_w=W - 64 - (64 + tw + 72) - 48)
    return c


def v3_split(d):
    """Photo on top 60 %, black panel below: model, specs in a row, large price."""
    c = Image.new("RGB", (W, H), (12, 12, 14))
    ph = 1100
    c.paste(_photo(d["main"], W, ph), (0, 0))
    c = _vgrad(c, 0, 300, 0.6, 0.0)
    c = _vgrad(c, ph - 260, ph, 0.0, 1.0, color=(12, 12, 14))
    dr = ImageDraw.Draw(c)
    brand, model = _split(d["title"])
    dr.text((64, 150), brand.upper(), font=_fit(brand.upper(), F_BRAND, 66, W - 128), fill="white")
    dr.text((64, ph - 20), model.upper(), font=_fit(model.upper(), F_ITALIC, 72, W - 128), fill="white")
    y = ph + 110
    cols = (("ГОД", d["year"], ms.icon_calendar()), ("ПРОБЕГ", mileage_text(d["mileage"]), ms.icon_speedometer()))
    cw = (W - 128) // 2
    for k, (lab, val, ic) in enumerate(cols):
        x = 64 + k * cw
        _icon(c, ic, x, y, 50, (200, 200, 205))
        dr.text((x + 70, y + 2), lab, font=_font(F_REG, 30), fill=(160, 160, 166))
        dr.text((x, y + 70), val, font=_font(F_BOLD, 54), fill="white")
    dr.line([(64, y + 180), (W - 64, y + 180)], fill=(60, 60, 66), width=2)
    for k, col in enumerate(((33, 70, 196), (255, 255, 255), ACCENT)):
        dr.rectangle([64 + k * 50, y + 220, 64 + k * 50 + 44, y + 228], fill=col)
    dr.text((64, y + 250), "Цена под ключ", font=_font(F_REG, 38), fill=(170, 170, 176))
    dr.text((64, y + 298), f"{d['price']} ₽", font=_fit(f"{d['price']} ₽", F_BOLD, 112, W - 128), fill="white")
    return c


def v4_cards_badge(d):
    """Like format A (two cards on a dark backdrop) but centred title and a red price badge."""
    bg = ms.collage_backdrop(d["main"])
    c = ms.dark_overlay(bg, 560, end=700)
    dr = ImageDraw.Draw(c)
    brand, model = _split(d["title"])
    for text, f, y, col in ((brand.upper(), _fit(brand.upper(), F_BRAND, 64, W - 128), 140, "white"),
                            (model.upper(), _fit(model.upper(), F_ITALIC, 58, W - 128), 214, (225, 225, 225))):
        dr.text(((W - ms.text_width(text, f)) // 2, y), text, font=f, fill=col)
    line = f"{d['year']}   •   {mileage_text(d['mileage'])}"
    lf = _font(F_REG, 40)
    dr.text(((W - ms.text_width(line, lf)) // 2, 304), line, font=lf, fill=(210, 210, 214))
    pf = _font(F_BOLD, 70)
    txt = f"{d['price']} ₽"
    tw = ms.text_width(txt, pf)
    bx = (W - tw - 80) // 2
    dr.rounded_rectangle([bx, 380, bx + tw + 80, 490], radius=55, fill=ACCENT)
    dr.text((bx + 40, 392), txt, font=pf, fill="white")
    sub = "цена под ключ"
    sf = _font(F_REG, 30)
    dr.text(((W - ms.text_width(sub, sf)) // 2, 505), sub, font=sf, fill=(190, 190, 196))
    cw = W - 2 * 48
    top = 590
    gap = 24
    h = (H - 118 - top - gap) // 2
    imgs = [d.get("second") or d["main"], d["main"]]
    for k, pth in enumerate(imgs):
        p = _photo(pth, cw, h)
        c.paste(p, (48, top + k * (h + gap)), _round(p, 28))
    return c


VARIANTS = {"1_hero": v1_hero, "2_light": v2_light, "3_split": v3_split, "4_cards_badge": v4_cards_badge}


# ------------------------------------------------- selling variants (DA Motors)
INK = (20, 20, 22)
GREY = (112, 112, 118)
BG = (244, 243, 240)
CARD = (255, 255, 255)
BENEFITS = [("globe", "Из Южной Кореи"), ("doc", "Растаможка и ЭПТС включены"),
            ("truck", "Доставка до Москвы/Санкт-Петербурга включена"), ("clock", "Доставка до 45 дней")]
CTA = "Узнать подробности"
# CTA phrases rotate by post number so a row of stories does not repeat one line
CTAS = ["Узнать подробности"]

FACT_RULES = [(r"без\s+дтп", "Без ДТП"), (r"падени", "Без падений"),
              (r"перв\w*\s+владел|1\s*владел|один\s+владел", "1 владелец"),
              (r"кофр", "Кофры в комплекте"), (r"quick\s*shift|квикшифт", "Квикшифтер"),
              (r"сервисн\w*\s+книж|обслуживал", "Обслуживался"), (r"гаранти", "На гарантии")]


def facts_from(text, limit=3):
    """Short facts taken literally from the post description (only what the post says)."""
    t = (text or "").lower()
    out = [label for rx, label in FACT_RULES if re.search(rx, t)]
    return out[:limit]


def _ss_icon(kind, size, color, bg=None):
    """Simple line icons drawn 4x and scaled down: globe, doc, truck, clock, check, arrow."""
    S = size * 4; m = Image.new("L", (S, S), 0); d = ImageDraw.Draw(m); w = max(4, S // 11)
    if kind == "globe":
        d.ellipse([w, w, S - w, S - w], outline=255, width=w)
        d.ellipse([S * .3, w, S * .7, S - w], outline=255, width=w)
        d.line([(w, S / 2), (S - w, S / 2)], fill=255, width=w)
    elif kind == "doc":
        d.rounded_rectangle([S * .18, w, S * .82, S - w], radius=S // 10, outline=255, width=w)
        for k in range(3):
            y = S * (.34 + k * .17); d.line([(S * .32, y), (S * .68 if k < 2 else S * .52, y)], fill=255, width=w)
    elif kind == "truck":
        d.rounded_rectangle([w, S * .26, S * .62, S * .7], radius=S // 16, outline=255, width=w)
        d.polygon([(S * .62, S * .4), (S * .8, S * .4), (S - w, S * .55), (S - w, S * .7), (S * .62, S * .7)], outline=255)
        d.line([(S * .62, S * .4), (S * .8, S * .4), (S - w, S * .55), (S - w, S * .7), (S * .62, S * .7)], fill=255, width=w)
        for cx in (S * .25, S * .78):
            d.ellipse([cx - S * .11, S * .66, cx + S * .11, S * .88], fill=0, outline=255, width=w)
    elif kind == "clock":
        d.ellipse([w, w, S - w, S - w], outline=255, width=w)
        d.line([(S / 2, S * .22), (S / 2, S / 2), (S * .7, S * .62)], fill=255, width=w, joint="curve")
    elif kind == "check":
        d.line([(S * .2, S * .52), (S * .42, S * .74), (S * .82, S * .28)], fill=255, width=int(w * 1.4), joint="curve")
    elif kind == "arrow":
        d.line([(S * .15, S / 2), (S * .82, S / 2)], fill=255, width=w)
        d.line([(S * .55, S * .25), (S * .84, S / 2), (S * .55, S * .75)], fill=255, width=w, joint="curve")
    return m.resize((size, size), Image.LANCZOS)


def _put_icon(c, kind, x, y, size, color):
    x, y, size = int(x), int(y), int(size)
    c.paste(color, (x, y, x + size, y + size), _ss_icon(kind, size, color))


def _rr(c, box, r, fill):
    """Antialiased rounded rectangle."""
    x0, y0, x1, y1 = [int(v) for v in box]
    tile = Image.new("RGB", (x1 - x0, y1 - y0), fill)
    c.paste(tile, (x0, y0), _round(tile, r))


def _pic(c, path, box, r=28):
    x0, y0, x1, y1 = box
    p = _photo(path, x1 - x0, y1 - y0)
    c.paste(p, (x0, y0), _round(p, r) if r else None)


def _gallery(d, n):
    ph = [p for p in (d.get("photos") or []) if p]
    if not ph:
        ph = [d["main"]] + ([d["second"]] if d.get("second") else [])
    while len(ph) < n:
        ph.append(ph[len(ph) % max(1, len(ph))])
    return ph[:n]


def _title(c, d, x, y, size=66, col=INK, sub=GREY, max_w=None, center=False):
    dr = ImageDraw.Draw(c)
    brand, model = _split(d["title"])
    max_w = max_w or W - 2 * x
    fb = _fit(brand.upper(), F_BRAND, size, max_w); fm = _fit(model.upper(), F_ITALIC, int(size * .86), max_w)
    for t, f, yy, cl in ((brand.upper(), fb, y, col), (model.upper(), fm, y + int(size * 1.12), sub)):
        xx = (W - ms.text_width(t, f)) // 2 if center else x
        dr.text((xx, yy), t, font=f, fill=cl)
    return y + int(size * 1.12) + int(size * .86) + 10


def _chip(c, x, y, text, size=32, fill=CARD, color=INK, icon=None, icol=ACCENT, pad=26, h=None):
    f = _font(F_BOLD, size); h = h or int(size * 2.1)
    iw = int(size * 1.1) + 12 if icon else 0
    w = pad * 2 + iw + ms.text_width(text, f)
    _rr(c, (x, y, x + w, y + h), h // 2, fill)
    if icon:
        _put_icon(c, icon, x + pad, y + (h - int(size * 1.1)) // 2, int(size * 1.1), icol)
    ImageDraw.Draw(c).text((x + pad + iw, y + (h - size) // 2 - int(size * .12)), text, font=f, fill=color)
    return x + w


def _chips_flow(c, x, y, items, max_x, gap=14, **kw):
    """Lay chips left to right, wrapping; returns the y below the last row."""
    size = kw.get("size", 32); h = kw.get("h") or int(size * 2.1)
    cx = x
    for it in items:
        icon, text = it if isinstance(it, tuple) else (None, it)
        f = _font(F_BOLD, size)
        w = 2 * kw.get("pad", 26) + (int(size * 1.1) + 12 if icon else 0) + ms.text_width(text, f)
        if cx + w > max_x and cx > x:
            cx = x; y += h + gap
        cx = _chip(c, cx, y, text, icon=icon, **kw) + gap
    return y + h


def _cta(c, box, text=CTA, fill=INK, color=(255, 255, 255), size=44):
    x0, y0, x1, y1 = box
    _rr(c, box, (y1 - y0) // 2, fill)
    f = _font(F_BOLD, size); aw = int(size * 1.0)
    tw = ms.text_width(text, f) + 22 + aw
    tx = x0 + (x1 - x0 - tw) // 2
    ImageDraw.Draw(c).text((tx, y0 + (y1 - y0 - size) // 2 - int(size * .12)), text, font=f, fill=color)
    _put_icon(c, "arrow", tx + tw - aw, y0 + (y1 - y0 - aw) // 2, aw, color)


def _price_block(c, x, y, d, size=88, pill=True):
    dr = ImageDraw.Draw(c)
    dr.text((x, y), "Цена под ключ с ЭПТС", font=_font(F_REG, 34), fill=GREY)
    txt = f"{d['price']} ₽"; pf = _font(F_BOLD, size); tw = ms.text_width(txt, pf)
    if pill:
        h = int(size * 1.5)
        _rr(c, (x, y + 50, x + tw + 2 * int(size * .45), y + 50 + h), h // 2, ACCENT)
        dr.text((x + int(size * .45), y + 50 + (h - size) // 2 - int(size * .12)), txt, font=pf, fill="white")
        return x + tw + 2 * int(size * .45), y + 50 + h
    dr.text((x, y + 44), txt, font=pf, fill=ACCENT)
    return x + tw, y + 44 + int(size * 1.15)


def _specs_line(d):
    return [("calendar", d["year"]), ("speed", mileage_text(d["mileage"]))]


def _spec_cards(c, x0, y, x1, items, h=128):
    """White cards in a row: small grey label, bold value."""
    n = len(items); gap = 16; w = (x1 - x0 - gap * (n - 1)) // n
    dr = ImageDraw.Draw(c)
    for k, (lab, val) in enumerate(items):
        x = x0 + k * (w + gap)
        _rr(c, (x, y, x + w, y + h), 26, CARD)
        dr.text((x + 28, y + 14), lab, font=_font(F_REG, 30), fill=GREY)
        dr.text((x + 28, y + 50), val, font=_fit(val, F_BOLD, 46, w - 56), fill=INK)
    return y + h


def _logo_top(c, d, y=196, x=64, width=300):
    if LOGO.exists():
        lg = Image.open(LOGO).convert("RGBA"); lg = lg.resize((width, round(lg.height * width / lg.width)), Image.LANCZOS)
        c.paste(lg, (x, y), lg)
        return y + lg.height
    return y


def v5_catalog(d):
    """Photos first: big photo + row of three, spec cards, benefits with ticks, price pill, CTA."""
    c = Image.new("RGB", (W, H), BG); dr = ImageDraw.Draw(c)
    L, R = 64, W - 64
    _logo_top(c, d, y=200, width=280)
    _chip(c, R - 330, 196, "из Южной Кореи", size=28, icon="globe", h=58, pad=20)
    y = _title(c, d, L, 290, size=60)
    import story_a2                                     # whole-bike crop, shared with VELTOR
    ph = _gallery(d, 4)
    uniq = list(dict.fromkeys(ph))
    ph = story_a2.order_for_main(uniq) + ph[len(uniq):]
    p, mh = story_a2.photo_whole(ph[0], R - L, 510, 600)     # taller card only if the bike needs it
    c.paste(p, (L, y + 10), _round(p, 34))
    extra = mh - 510                                         # given back by thumbnails, then the 3rd tick line
    th = 170 - min(50, extra)
    drop_fact = extra > 50
    y0 = y + 10 + mh + 16
    tw = (R - L - 2 * 16) // 3
    for k in range(3):
        _pic(c, ph[k + 1], (L + k * (tw + 16), y0, L + k * (tw + 16) + tw, y0 + th), 24)
    y = _spec_cards(c, L, y0 + th + 20, R, [("Год", d["year"]), ("Пробег", mileage_text(d["mileage"])), ("Срок", "до 45 дней")], h=112)
    y += 22
    for k, txt in enumerate(["Растаможка и ЭПТС включены", "Доставка до Москвы/Санкт-Петербурга включена"] + ([] if drop_fact else d.get("facts", [])[:1])):
        _rr(c, (L, y + 4, L + 44, y + 48), 22, ACCENT); _put_icon(c, "check", L + 6, y + 10, 32, (255, 255, 255))
        dr.text((L + 64, y + 4), txt, font=_fit(txt, F_BOLD, 36, R - L - 64), fill=INK); y += 56
    px, py = _price_block(c, L, y + 14, d, size=76)
    _cta(c, (L, py + 24, R, py + 124), text=d.get("cta") or CTA, size=42)
    return c


def v6_sheet(d):
    """Full-bleed photo on top, light sheet below with thumbnails, chips, price and CTA in one row."""
    c = Image.new("RGB", (W, H), BG)
    ph = _gallery(d, 4)
    c.paste(_photo(ph[0], W, 820), (0, 0))
    c = _vgrad(c, 0, 360, 0.42, 0.0)
    _rr(c, (64, 196, 64 + 340, 196 + 92), 46, CARD)
    if LOGO.exists():
        lg = Image.open(LOGO).convert("RGBA"); lg = lg.resize((270, round(lg.height * 270 / lg.width)), Image.LANCZOS)
        c.paste(lg, (64 + 35, 196 + (92 - lg.height) // 2), lg)
    sheet = Image.new("RGB", (W, H - 760), BG)
    m = Image.new("L", sheet.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, W - 1, H], radius=56, fill=255)
    c.paste(sheet, (0, 760), m)
    dr = ImageDraw.Draw(c); L, R = 64, W - 64
    y = _title(c, d, L, 806, size=62)
    dr.text((L, y), f"{d['year']}  •  {mileage_text(d['mileage'])}", font=_font(F_BOLD, 40), fill=INK)
    y += 72
    tw = (R - L - 2 * 16) // 3
    for k in range(3):
        _pic(c, ph[k + 1], (L + k * (tw + 16), y, L + k * (tw + 16) + tw, y + 190), 24)
    y += 214
    items = [("globe", "Из Южной Кореи"), ("doc", "Растаможка и ЭПТС"), ("truck", "Доставка до Москвы"),
             ("clock", "До 45 дней")] + [("check", f) for f in d.get("facts", [])[:1]]
    y = _chips_flow(c, L, y, items, R, size=30, h=66, pad=22, gap=12)
    y += 34
    px, py = _price_block(c, L, y, d, size=80)
    _cta(c, (L, py + 26, R, py + 126), fill=INK, size=42)
    return c


def v7_tiles(d):
    """Mosaic of three photos + four benefit tiles with icons; price with logo; red CTA."""
    c = Image.new("RGB", (W, H), BG); dr = ImageDraw.Draw(c)
    L, R = 64, W - 64
    y = _title(c, d, L, 200, size=62)
    dr.text((L, y), f"{d['year']}  •  {mileage_text(d['mileage'])}" + (f"  •  {d['facts'][0]}" if d.get("facts") else ""),
            font=_font(F_BOLD, 38), fill=INK)
    y += 70
    ph = _gallery(d, 3)
    bw = 600
    _pic(c, ph[0], (L, y, L + bw, y + 640), 32)
    sh = (640 - 16) // 2
    _pic(c, ph[1], (L + bw + 16, y, R, y + sh), 26)
    _pic(c, ph[2], (L + bw + 16, y + sh + 16, R, y + 640), 26)
    y += 664
    tw = (R - L - 16) // 2; th = 150
    labels = [("globe", "Из Южной", "Кореи"), ("doc", "Растаможка", "и ЭПТС включены"),
              ("truck", "Доставка", "до Москвы включена"), ("clock", "Срок доставки", "до 45 дней")]
    for k, (ic, a, b) in enumerate(labels):
        x = L + (k % 2) * (tw + 16); yy = y + (k // 2) * (th + 16)
        _rr(c, (x, yy, x + tw, yy + th), 28, CARD)
        _rr(c, (x + 24, yy + (th - 84) // 2, x + 108, yy + (th + 84) // 2), 42, (252, 233, 233))
        _put_icon(c, ic, x + 42, yy + (th - 48) // 2, 48, ACCENT)
        dr.text((x + 130, yy + 34), a, font=_font(F_BOLD, 34), fill=INK)
        dr.text((x + 130, yy + 80), b, font=_fit(b, F_REG, 30, tw - 150), fill=GREY)
    y += 2 * th + 16 + 34
    px, py = _price_block(c, L, y, d, size=80)
    _logo(c, right=R, cy=py - 60, max_w=R - px - 40, width=300)
    _cta(c, (L, py + 26, R, py + 126), fill=ACCENT, size=42)
    return c


def v8_offer(d):
    """Price first: logo, 'под ключ' headline, big red price, 2x2 photo grid, model, benefit chips, CTA."""
    c = Image.new("RGB", (W, H), BG); dr = ImageDraw.Draw(c)
    L, R = 64, W - 64
    if LOGO.exists():
        lg = Image.open(LOGO).convert("RGBA"); lg = lg.resize((300, round(lg.height * 300 / lg.width)), Image.LANCZOS)
        c.paste(lg, ((W - lg.width) // 2, 196), lg)
    head = "ПОД КЛЮЧ С ЭПТС И ДОСТАВКОЙ ДО МОСКВЫ"
    hf = _fit(head, F_BRAND, 44, R - L)
    dr.text(((W - ms.text_width(head, hf)) // 2, 290), head, font=hf, fill=INK)
    txt = f"{d['price']} ₽"; pf = _fit(txt, F_BOLD, 132, R - L)
    dr.text(((W - ms.text_width(txt, pf)) // 2, 352), txt, font=pf, fill=ACCENT)
    y = 530
    ph = _gallery(d, 4); gw = (R - L - 16) // 2; gh = 330
    for k in range(4):
        x = L + (k % 2) * (gw + 16); yy = y + (k // 2) * (gh + 16)
        _pic(c, ph[k], (x, yy, x + gw, yy + gh), 28)
    y += 2 * gh + 16 + 34
    y = _title(c, d, L, y, size=56, center=True)
    line = f"{d['year']}  •  {mileage_text(d['mileage'])}"
    lf = _font(F_BOLD, 40); dr.text(((W - ms.text_width(line, lf)) // 2, y), line, font=lf, fill=INK)
    y += 76
    items = [("globe", "Из Южной Кореи"), ("clock", "До 45 дней")] + [("check", f) for f in d.get("facts", [])[:2]]
    f = _font(F_BOLD, 30)
    widths = [2 * 22 + 45 + ms.text_width(t, f) for _, t in items]
    while sum(widths) + 12 * (len(widths) - 1) > R - L:
        items.pop(); widths.pop()
    x = (W - sum(widths) - 12 * (len(widths) - 1)) // 2
    for it in items:
        x = _chip(c, x, y, it[1], size=30, h=66, pad=22, icon=it[0]) + 12
    _cta(c, (L, y + 110, R, y + 210), fill=INK, size=42)
    return c


def v9_panel(d):
    """Light top with photo collage and facts, dark rounded panel at the bottom: benefits, price, red CTA."""
    c = Image.new("RGB", (W, H), BG); dr = ImageDraw.Draw(c)
    L, R = 64, W - 64
    _logo(c, right=R, cy=236, max_w=320, width=280)
    y = _title(c, d, L, 200, size=60, max_w=R - L - 320)
    ph = _gallery(d, 3)
    _pic(c, ph[0], (L, y + 20, R, y + 560), 34)
    hw = (R - L - 16) // 2
    _pic(c, ph[1], (L, y + 576, L + hw, y + 800), 26)
    _pic(c, ph[2], (L + hw + 16, y + 576, R, y + 800), 26)
    fx = L + 24
    for t in [d["year"], mileage_text(d["mileage"])] + d.get("facts", [])[:1]:
        fx = _chip(c, fx, y + 44, t, size=28, h=60, pad=20) + 10
    py0 = y + 830
    panel = (24, py0, W - 24, H - 150)
    _rr(c, panel, 48, (22, 22, 24))
    yy = py0 + 40
    for k, (ic, t) in enumerate(BENEFITS):
        x = L + 16 + (k % 2) * ((R - L) // 2); y2 = yy + (k // 2) * 62
        _put_icon(c, ic, x, y2 + 4, 38, ACCENT)
        dr.text((x + 54, y2 + 4), t if len(t) < 22 else t.replace(" включены", "").replace(" включена", ""),
                font=_font(F_BOLD, 30), fill=(235, 235, 238))
    yy += 140
    dr.text((L + 16, yy), "Цена под ключ с ЭПТС", font=_font(F_REG, 32), fill=(170, 170, 176))
    txt = f"{d['price']} ₽"
    dr.text((L + 16, yy + 42), txt, font=_fit(txt, F_BOLD, 92, R - L - 32), fill="white")
    _cta(c, (L + 16, panel[3] - 40 - 96, R - 16, panel[3] - 40), fill=ACCENT, size=42)
    return c


VARIANTS.update({"5_catalog": v5_catalog, "6_sheet": v6_sheet, "7_tiles": v7_tiles,
                 "8_offer": v8_offer, "9_panel": v9_panel})


def build_b(variant, main, second, title, year, mileage, price_in_group, out, photos=None, description="", post_id=0):
    d = {"main": main, "second": second, "title": title, "year": year, "mileage": mileage,
         "price": price_plus(price_in_group), "photos": photos, "facts": facts_from(description),
         "cta": CTAS[int(post_id or 0) % len(CTAS)]}
    img = VARIANTS[variant](d)
    img.save(out, quality=95, subsampling=0)
    return out
