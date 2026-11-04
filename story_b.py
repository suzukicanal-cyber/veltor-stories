#!/usr/bin/env python3
"""Format B stories (second channel): same Moto posts and the same 5 lines,
price + 50 000 ₽, delivered to a separate chat. Several design variants;
the chosen one is set in config.json ("format_b": {"variant": "..."}).
Format A (make_story.py) is not touched.
"""
import re

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


def build_b(variant, main, second, title, year, mileage, price_in_group, out):
    d = {"main": main, "second": second, "title": title, "year": year, "mileage": mileage,
         "price": price_plus(price_in_group)}
    img = VARIANTS[variant](d)
    img.save(out, quality=95, subsampling=0)
    return out
