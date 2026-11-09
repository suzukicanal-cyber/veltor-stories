#!/usr/bin/env python3
"""VELTOR stories for the «Авто» topic (group «Сторисы»): same visual language as the
moto stories (black with a light glow, VELTOR wordmark, Montserrat), car data from the post:
model, year, mileage, engine, drive, gearbox, price «под ключ в Москве», equipment.
Draft variants c1..c5; the chosen one goes to config.json.
"""
import re

from PIL import Image, ImageDraw

import detect
import make_story as ms
import story_a2 as a2
import story_b as sb
from story_a2 import F, L, R, W, H, M5, M6, M7, WHITE, SOFT, text, tw, fit

INK = (14, 14, 16)
LINE = (80, 80, 86)


# ---------------------------------------------------------------- post text
def parse_car(text_):
    lines = [l.strip() for l in text_.splitlines() if l.strip()]
    blob = "\n".join(lines[1:])
    g = lambda rx: (re.search(rx, blob, re.I) or [None, None])[1]
    price = re.search(r"Цена[^:\n]*:\s*\n?\s*([\d\s ]+?)\s*(?:₽|руб)", blob, re.I)
    d = {"title": lines[0], "year": g(r"Год\s*[:\-–]?\s*(\d{4})"),
         "mileage": g(r"Пробег\s*[:\-–]?\s*([\d’'`\s .,]+?)\s*(?:km|км)\b"),
         "price": re.sub(r"[\s ]+", " ", price.group(1)).strip() if price else None,
         "hp": g(r"Двигатель\s*[:\-–]?\s*(\d{2,4})\s*л\.?\s*с"),
         "drive": g(r"Привод\s*[:\-–]?\s*([^\n]+)"),
         "gearbox": g(r"Коробка\s*[:\-–]?\s*([^\n]+)"),
         "no_accident": bool(re.search(r"без\s+дтп", blob, re.I)),
         "price_label": "ЦЕНА ПОД КЛЮЧ В МОСКВЕ" if re.search(r"под\s+ключ\s+в\s+москв", blob, re.I) else "ЦЕНА ПОД КЛЮЧ",
         "util": bool(re.search(r"утилизационн\w*\s+сбор\s+уже\s+включ", blob, re.I))}
    if d["mileage"]:
        d["mileage"] = re.sub(r"\s+", "", d["mileage"])
    if d["gearbox"]:
        gb = d["gearbox"].lower()
        d["gearbox_short"] = "DSG" if "dsg" in gb else "робот" if "робот" in gb else \
            "механика" if "механ" in gb else "вариатор" if "вариат" in gb else "автомат"
    missing = [k for k in ("year", "mileage", "price") if not d[k]]
    if missing:
        raise ValueError("нет строк: " + ", ".join(missing))
    return d


EQUIP = [(r"панорам", "Панорамная крыша"), (r"\bлюк\b", "Люк"), (r"проекционн|\bhud\b", "Проекционный дисплей"),
         (r"360", "Камеры 360°"), (r"массаж", "Массаж сидений"), (r"вентиляц\w*\s+(?:передн\w*\s+)?сид", "Вентиляция сидений"),
         (r"адаптивн\w*\s+круиз", "Адаптивный круиз"), (r"электропривод\s+багажник", "Электробагажник"),
         (r"доводчик", "Доводчики дверей"), (r"кожан\w*\s+салон", "Кожаный салон"),
         (r"подогрев\s+руля", "Подогрев руля"), (r"мониторинг\s+слеп|контроль\s+слеп", "Контроль слепых зон")]


def equipment(text_, limit=6):
    t = text_.lower()
    return [lab for rx, lab in EQUIP if re.search(rx, t)][:limit]


# ---------------------------------------------------------------- photos
def car_box(path):
    bs = detect.car_boxes(path)
    if not bs:
        return None
    return max(bs, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]) * b[4])


def classify(paths):
    """Exterior shots (a whole car, large) in album order, and interior shots."""
    ext, inside = [], []
    for p in paths:
        b = car_box(p)
        area = (b[2] - b[0]) * (b[3] - b[1]) if b else 0
        cut = sum([b[0] < 0.01, b[1] < 0.01, b[2] > 0.99, b[3] > 0.99]) if b else 4
        (ext if b and 0.12 < area < 0.9 and cut <= 1 else inside).append(p)
    return ext, inside


def pick(paths):
    """main = first whole exterior (dealer albums start with the front 3/4 view),
    then: second exterior, two interior shots (dashboard first, then seats)."""
    ext, inside = classify(paths)
    main = ext[0] if ext else paths[0]
    rest_ext = [p for p in ext if p != main]
    inner = [inside[0], inside[len(inside) // 2]] if len(inside) >= 2 else inside
    inner = list(dict.fromkeys(inner))
    others = rest_ext[:1] + inner + rest_ext[1:] + [p for p in inside if p not in inner]
    return [main] + [p for p in others if p != main], main


def main_card(c, path, y, h_min, h_max, r=30):
    b = car_box(path)
    p, h = a2.photo_whole(path, R - L, h_min, h_max, margin=0.05, box=b[:4] if b else None)
    c.paste(p, (L, y), sb._round(p, r))
    return y + h


# ---------------------------------------------------------------- pieces
def specs_row(c, items, y, size=40):
    """Evenly spread columns with thin dividers: [(label, value), ...]."""
    n = len(items); cw = (R - L) / n
    fl = F(M5, 22)
    dr = ImageDraw.Draw(c)
    for k, (lab, val) in enumerate(items):
        x = L + k * cw + (0 if k == 0 else 26)
        fv = fit(val, M6, size, cw - 34)
        text(c, (x, y), lab, fl, SOFT, tracking=4)
        text(c, (x, y + 34), val, fv, WHITE)
        if k:
            dr.line([(L + k * cw, y + 4), (L + k * cw, y + 84)], fill=LINE, width=2)
    return y + 92


def spec_items(d, n=4):
    items = [("ГОД", d["year"]), ("ПРОБЕГ", f"{d['mileage']} km")]
    if d.get("hp"):
        items.append(("МОЩНОСТЬ", f"{d['hp']} л.с."))
    if d.get("drive"):
        items.append(("ПРИВОД", d["drive"]))
    elif d.get("gearbox_short"):
        items.append(("КОРОБКА", d["gearbox_short"]))
    return items[:n]


def price_pill(c, d, y, glow="white", h=132, size=92):
    text(c, (L, y), d["price_label"], F(M5, 26), SOFT, tracking=6)
    a2_fill = (246, 246, 244) if glow == "white" else a2.GLOWS["red"]
    sb._rr(c, (L, y + 44, R, y + 44 + h), h // 2, a2_fill)
    s = f"{d['price']} ₽"
    f = fit(s, M7, size, R - L - 80)
    text(c, (L, y + 44 + (h - f.size) // 2 - 10), s, f, INK if glow == "white" else WHITE, center=True)
    return y + 44 + h


def note(c, s, y, center=True):
    text(c, (L, y), s, fit(s, M5, 24, R - L, tracking=4), SOFT, tracking=4, center=center)


def head(c, d, y=300):
    return a2.title(c, d, y, size=70)


def _base(glow="white", center=0.47):
    c, _ = a2.background(glow, "band", center=center)
    a2.wordmark(c); a2.corner_tag(c)
    return c


# ---------------------------------------------------------------- variants
def c1_showcase(d, glow="white"):
    """As the moto story: big exterior, three photos below, four specs, price pill."""
    c = _base(glow)
    y = head(c, d)
    ph = d["photos"]
    y = main_card(c, ph[0], y + 24, 620, 680)
    y = a2.thumbs(c, ph[1:4], y + 16, 220)
    y = specs_row(c, spec_items(d), y + 40)
    price_pill(c, d, y + 34, glow)
    return c


def c2_equipment(d, glow="white"):
    """Exterior + interior side by side under it, specs, a line of equipment highlights."""
    c = _base(glow)
    y = head(c, d)
    ph = d["photos"]
    y = main_card(c, ph[0], y + 24, 580, 640)
    hw = (R - L - 14) // 2
    sb._pic(c, ph[2] if len(ph) > 2 else ph[1], (L, y + 14, L + hw, y + 264), 22)
    sb._pic(c, ph[3] if len(ph) > 3 else ph[1], (L + hw + 14, y + 14, R, y + 264), 22)
    y = specs_row(c, spec_items(d), y + 304)
    eq = d.get("equipment") or []
    if eq:
        y = a2.facts(c, {"facts": eq}, y + 22)
    price_pill(c, d, y + 34, glow, h=120, size=84)
    return c


def c3_interior(d, glow="white"):
    """Two big cards: the exterior and the interior; one quiet line of specs."""
    c = _base(glow, center=0.5)
    y = head(c, d)
    ph = d["photos"]
    y = main_card(c, ph[0], y + 24, 560, 620)
    inner = ph[2] if len(ph) > 2 else ph[1]
    sb._pic(c, inner, (L, y + 14, R, y + 444), 30)
    y += 444 + 40
    line = "  ·  ".join(v for _, v in spec_items(d, 4))
    text(c, (L, y), line, fit(line, M6, 36, R - L), WHITE, center=True)
    price_pill(c, d, y + 70, glow, h=120, size=84)
    return c


def c4_grid(d, glow="white"):
    """Four photos 2x2 (outside and inside), specs, price."""
    c = _base(glow, center=0.45)
    y = head(c, d)
    ph = (d["photos"] + d["photos"])[:4]
    gw = (R - L - 14) // 2; gh = 400
    for k in range(4):
        x = L + (k % 2) * (gw + 14); yy = y + 24 + (k // 2) * (gh + 14)
        if k == 0:
            b = car_box(ph[0])
            p, _ = a2.photo_whole(ph[0], gw, gh, gh, margin=0.05, box=b[:4] if b else None)
            c.paste(p, (x, yy), sb._round(p, 24))
        else:
            sb._pic(c, ph[k], (x, yy, x + gw, yy + gh), 24)
    y += 24 + 2 * gh + 14
    y = specs_row(c, spec_items(d), y + 40)
    price_pill(c, d, y + 34, glow)
    return c


def c5_details(d, glow="white"):
    """Big exterior, a two-column spec sheet (year, mileage, engine, drive, gearbox, accidents), price."""
    c = _base(glow, center=0.36)
    y = head(c, d)
    ph = d["photos"]
    y = main_card(c, ph[0], y + 24, 620, 680)
    rows = [("Год", d["year"]), ("Пробег", f"{d['mileage']} km")]
    if d.get("hp"): rows.append(("Двигатель", f"{d['hp']} л.с."))
    if d.get("drive"): rows.append(("Привод", d["drive"]))
    if d.get("gearbox"): rows.append(("Коробка", d["gearbox"]))
    if d.get("no_accident"): rows.append(("История", "без ДТП"))
    rows = rows[:6]
    y += 30
    dr = ImageDraw.Draw(c)
    cw = (R - L - 40) // 2; rh = 74
    fl, fv = F(M5, 30), F(M6, 34)
    for k, (lab, val) in enumerate(rows):
        x = L + (k % 2) * (cw + 40); yy = y + (k // 2) * rh
        text(c, (x, yy + 14), lab, fl, SOFT)
        v = fit(val, M6, 34, cw - tw(lab, fl) - 24)
        text(c, (x + cw, yy + 14), val, v, WHITE, anchor_right=True)
        dr.line([(x, yy + rh - 4), (x + cw, yy + rh - 4)], fill=(60, 60, 66), width=1)
    y += ((len(rows) + 1) // 2) * rh + 30
    y = price_pill(c, d, y, glow)
    if d.get("util"):
        note(c, "УТИЛЬСБОР ВКЛЮЧЁН — БЕЗ СКРЫТЫХ ДОПЛАТ", y + 30)
    return c


VARIANTS = {"c1_showcase": c1_showcase, "c2_equipment": c2_equipment, "c3_interior": c3_interior,
            "c4_grid": c4_grid, "c5_details": c5_details}


def build_auto(variant, photos, post_text, out, glow="white"):
    d = parse_car(post_text)
    d["photos"], _ = pick(photos)
    d["equipment"] = equipment(post_text)
    d["facts"] = d["equipment"]
    img = VARIANTS[variant](d, glow)
    img.save(out, quality=95, subsampling=0)
    return out
