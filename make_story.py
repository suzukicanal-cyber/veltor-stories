#!/usr/bin/env python3
"""VELTOR story card generator (1080x1920, 9:16, sRGB).

Overlays the approved template (dark top, title, 3 info rows with outline
icons, blue-white-red stripe) onto ONE original photo. The photo itself is
only scaled/cropped and faded into black at the edges - never altered.

Usage:
  make_story.py PHOTO OUT.jpg --title "Triumph Rocket 3" --year 2021 \
      --mileage "11’915" --price "1 667 000" [--zoom 1.0] [--focus-x 0.5]
"""
import argparse, math, re
from PIL import Image, ImageDraw, ImageFont, ImageCms, ImageChops

W, H = 1080, 1920
SS = 4  # supersampling for vector-ish elements

import os
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts") + "/"
F_LABEL = FONT_DIR + "Inter-Regular.otf"
F_VALUE = FONT_DIR + "Inter-Bold.otf"
F_MODEL = FONT_DIR + "InterDisplay-BlackItalic.otf"
F_BRAND = FONT_DIR + "texgyreheroscn-bold.otf"

# --- layout (derived from the approved reference, scaled to 1080 wide) ---
X0 = 92                 # left edge of title / stripe
BRAND_CAP_TOP, BRAND_CAP_H = 250, 82
MODEL_CAP_TOP, MODEL_CAP_H = 382, 76
STRIPE_X, STRIPE_W = 91, 8
ICON_X, ICON_S = 128, 78
TEXT_X = 247
ROW_TOPS = [496, 620, 742]
LABEL_SIZE, VALUE_SIZE = 40, 62
LABEL_TO_VALUE = 44      # value cap top offset below label cap top
BLUE, WHITE, RED = (33, 70, 196), (255, 255, 255), (214, 36, 44)
INFO_BOTTOM = 830
TITLE_MAX_W = W - X0 - 70

MULTIWORD_BRANDS = ["MV Agusta", "Royal Enfield", "Moto Guzzi", "Harley Davidson",
                    "Indian Motorcycle", "CF Moto"]


def split_title(title):
    t = " ".join(title.split())
    for b in MULTIWORD_BRANDS:
        if t.lower().startswith(b.lower() + " "):
            return t[:len(b)], t[len(b):].strip()
    parts = t.split(" ", 1)
    return (parts[0], parts[1]) if len(parts) == 2 else (t, "")


def font_for_cap(path, cap_h):
    """Return a font sized so capital letters are cap_h px tall."""
    probe = ImageFont.truetype(path, 200)
    l, t, r, b = probe.getbbox("H")
    return ImageFont.truetype(path, max(8, round(200 * cap_h / (b - t))))


def draw_text_cap(img, xy, text, font, fill, tracking=0):
    """Draw text so the top of capitals lands exactly at xy[1]."""
    d = ImageDraw.Draw(img)
    cap_top = font.getbbox("H")[1]
    x, y = xy
    if tracking == 0:
        d.text((x, y - cap_top), text, font=font, fill=fill)
        return d.textlength(text, font=font)
    for ch in text:
        d.text((x, y - cap_top), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + tracking
    return x - xy[0] - tracking


def text_width(text, font, tracking=0):
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    return sum(d.textlength(c, font=font) for c in text) + tracking * max(0, len(text) - 1)


def silver_text_layer(text, font, cap_h, tracking):
    """White-to-silver vertical gradient text, returned as RGBA layer + width."""
    w = int(text_width(text, font, tracking)) + 60
    h = cap_h * 2 + 40
    mask = Image.new("L", (w, h), 0)
    draw_text_cap(mask, (10, 20), text, font, 255, tracking)
    grad = Image.new("RGB", (w, h))
    gd = ImageDraw.Draw(grad)
    for y in range(h):
        t = min(1, max(0, (y - 20) / cap_h))
        # bright top, slight silver dip, bright edge near bottom
        v = 255 - 70 * math.sin(math.pi * min(1, t * 1.05)) ** 1.5 if t < 0.95 else 230
        gd.line([(0, y), (w, y)], fill=(int(v), int(v), int(min(255, v + 4))))
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    layer.paste(grad, (0, 0), mask)
    return layer


# ---------------- icons (white outline, drawn at 4x) ----------------
def icon_canvas():
    return Image.new("L", (ICON_S * SS, ICON_S * SS), 0)


def icon_calendar():
    im = icon_canvas(); d = ImageDraw.Draw(im); s = SS; lw = 5 * s
    d.rounded_rectangle([5 * s, 11 * s, 73 * s, 73 * s], radius=9 * s, outline=255, width=lw)
    d.line([7 * s, 27 * s, 71 * s, 27 * s], fill=255, width=lw)
    for x in (23, 55):
        d.rounded_rectangle([(x - 3) * s, 3 * s, (x + 3) * s, 18 * s], radius=3 * s, fill=255)
    for r in range(3):
        for c in range(4):
            x = 18 + c * 14; y = 38 + r * 11
            if r == 2 and c == 3:
                continue
            d.rectangle([(x - 3.5) * s, (y - 3) * s, (x + 3.5) * s, (y + 3) * s], fill=255)
    return im


def icon_speedometer():
    im = icon_canvas(); d = ImageDraw.Draw(im); s = SS; lw = 5 * s
    cx, cy, r = 39, 44, 33
    d.arc([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s], start=145, end=395, fill=255, width=lw)
    for k in range(7):
        a = math.radians(160 + k * (220 / 6))
        r1, r2 = r - 9, r - 3
        d.line([(cx + r1 * math.cos(a)) * s, (cy + r1 * math.sin(a)) * s,
                (cx + r2 * math.cos(a)) * s, (cy + r2 * math.sin(a)) * s], fill=255, width=4 * s)
    a = math.radians(-50)
    d.line([cx * s, cy * s, (cx + 21 * math.cos(a)) * s, (cy + 21 * math.sin(a)) * s], fill=255, width=5 * s)
    d.ellipse([(cx - 6) * s, (cy - 6) * s, (cx + 6) * s, (cy + 6) * s], fill=255)
    d.rounded_rectangle([(cx - 7) * s, (cy + 18) * s, (cx + 7) * s, (cy + 23) * s], radius=2 * s, fill=255)
    return im


def icon_tag():
    big = Image.new("L", (ICON_S * SS * 2, ICON_S * SS * 2), 0)
    d = ImageDraw.Draw(big); s = SS * 2 // 2; lw = 5 * s
    o = big.size[0] // 2  # center of the big canvas
    # tag pointing up (drawn upright, rotated -45 later)
    pts = [(-17, -10), (0, -32), (17, -10), (17, 34), (-17, 34)]
    pts = [(o + x * s, o + y * s) for x, y in pts]
    d.line(pts + [pts[0], pts[1]], fill=255, width=lw, joint="curve")
    d.ellipse([o - 5 * s, o - 17 * s, o + 5 * s, o - 7 * s], outline=255, width=4 * s)
    d.rounded_rectangle([o - 7 * s, o + 6 * s, o + 7 * s, o + 22 * s], radius=2 * s, outline=255, width=4 * s)
    big = big.rotate(-45, resample=Image.BICUBIC)
    c = big.size[0] // 2; half = ICON_S * SS // 2
    return big.crop((c - half, c - half, c + half, c + half))


def paste_icon(canvas, icon4x, x, y):
    small = icon4x.resize((ICON_S, ICON_S), Image.LANCZOS)
    canvas.paste((255, 255, 255), (x, y, x + ICON_S, y + ICON_S), small)


# ---------------- photo ----------------
def smoothstep(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def place_photo(canvas, photo_path, zoom, focus_x, bottom_frac):
    src = Image.open(photo_path)
    src = ImageCms.profileToProfile(src, ImageCms.getOpenProfile(
        __import__("io").BytesIO(src.info["icc_profile"])), ImageCms.createProfile("sRGB"),
        outputMode="RGB") if src.info.get("icc_profile") else src.convert("RGB")
    scale = W / src.width * zoom
    pw, ph = round(src.width * scale), round(src.height * scale)
    photo = src.resize((pw, ph), Image.LANCZOS)
    left = int(min(max(0, focus_x * pw - W / 2), pw - W))
    photo = photo.crop((left, 0, left + W, ph))

    bottom = H - int(bottom_frac)          # bottom_frac = gap in px under the photo
    top = bottom - ph
    if top < 0:                             # very tall result: crop from the top
        photo = photo.crop((0, -top, W, ph)); ph = photo.height; top = 0

    # Area above the photo: a smooth vertical gradient from black to ONE tone
    # taken from the photo's background (no per-column colours, so nothing of
    # the motorcycle can be smeared upward).
    tone = background_tone(photo)
    free = content_free_rows(photo, tone)         # rows above the bike that may fade
    feather = int(min(260, max(70, free)))
    if top > 0:
        span = top + feather
        grad = Image.new("RGB", (W, span)); gd = ImageDraw.Draw(grad)
        for y in range(span):
            t = smoothstep(y / span) ** 1.3
            gd.line([(0, y), (W, y)], fill=tuple(int(c * t) for c in tone))
        canvas.paste(grad, (0, 0))
    mask = Image.new("L", (W, ph), 255)
    md = ImageDraw.Draw(mask)
    for y in range(ph):
        a = 1.0
        if top > 0 and y < feather:
            a = smoothstep(y / feather)
        if bottom < H and y > ph - 200:            # floor fades softly into black
            a = min(a, smoothstep((ph - y) / 200) ** 0.8)
        md.line([(0, y), (W, y)], fill=int(255 * a))
    if top > 0 and free < feather:
        # The bike reaches into the fade zone: only the background fades there,
        # the bike itself (handlebar, mirrors, screen) stays fully visible.
        keep = bike_mask(photo.crop((0, 0, W, feather)), tone)
        top_part = ImageChops.lighter(mask.crop((0, 0, W, feather)), keep)
        mask.paste(top_part, (0, 0))
    canvas.paste(photo, (0, top), mask)
    return top, bottom


def bike_mask(region, tone, thresh=45):
    """White where pixels differ clearly from the background tone (= bike parts)."""
    from PIL import ImageFilter
    w, h = region.size
    soft = region.filter(ImageFilter.GaussianBlur(4))            # ignore fine wall texture
    bg = region.resize((6, h), Image.BOX).resize((w, h), Image.BILINEAR)   # row-wise background
    diff = ImageChops.difference(soft, bg).convert("L")
    m = diff.point(lambda v: 255 if v > thresh else 0)
    return m.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(4))


def top_margin_ratio(photo_path):
    """Share of the photo height above the bike that is pure background.
    Small values mean the bike touches (or almost touches) the top edge."""
    im = Image.open(photo_path).convert("RGB")
    im = im.resize((W, round(im.height * W / im.width)), Image.BOX)
    return content_free_rows(im, background_tone(im)) / im.height


def background_tone(photo, bottom=False):
    """Median colour of a thin band at the photo's top (or bottom) edge."""
    h = max(8, photo.height // 25)
    band = photo.crop((0, photo.height - h, photo.width, photo.height) if bottom else (0, 0, photo.width, h))
    small = band.resize((64, 4), Image.BOX)
    px = sorted((small.getpixel((x, y)) for y in range(4) for x in range(64)), key=lambda c: sum(c))
    return px[len(px) // 2]


def content_free_rows(photo, tone, thresh=45, frac=0.04):
    """How many rows from the top contain only background (no bike parts).
    A row counts as 'content' when more than `frac` of its pixels differ from the
    background tone by more than `thresh`."""
    small = photo.resize((160, max(1, photo.height * 160 // photo.width)), Image.BOX)
    sw, sh = small.size
    # Background model: each row smoothed only horizontally, so slow lighting
    # changes (vignettes, gradients on the wall) are not mistaken for the bike.
    bg = small.resize((6, sh), Image.BOX).resize((sw, sh), Image.BILINEAR)
    px, bx = small.load(), bg.load()
    for y in range(sh):
        diff = sum(1 for x in range(sw)
                   if sum(abs(px[x, y][i] - bx[x, y][i]) for i in range(3)) > thresh * 3)
        if diff > frac * sw:
            return y * photo.height / sh
    return photo.height * 0.4


def dark_overlay(canvas, photo_top, end=None):
    """Soft black gradient: dark info area at the top, clear photo below."""
    start = INFO_BOTTOM - 60                       # dark behind the text down to here
    if end is None:
        end = max(photo_top + 40, INFO_BOTTOM + 380)   # long, gentle fade; barely touches the photo
    a = Image.new("L", (W, H), 0); d = ImageDraw.Draw(a)
    for y in range(H):
        if y <= start:
            v = 0.80 + 0.12 * (1 - y / start)       # slightly deeper at the very top
        elif y < end:
            t = (y - start) / (end - start)
            v = 0.80 * (0.5 + 0.5 * math.cos(math.pi * t))   # cosine ease: no visible band edge
        else:
            v = 0
        d.line([(0, y), (W, y)], fill=int(255 * v))
    return Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), canvas, a)


COLLAGE_BLEND = 240   # height of the soft cross-fade between the two photos


def load_srgb(path):
    src = Image.open(path)
    if src.info.get("icc_profile"):
        return ImageCms.profileToProfile(src, ImageCms.getOpenProfile(
            __import__("io").BytesIO(src.info["icc_profile"])), ImageCms.createProfile("sRGB"),
            outputMode="RGB")
    return src.convert("RGB")


def _fit_w(img, w):
    return img.resize((w, round(img.height * w / img.width)), Image.LANCZOS)


def _vignette(canvas, strength=0.35):
    """Soft darkening towards the left/right edges and corners (cinematic look)."""
    small = Image.new("L", (108, 192), 0); px = small.load()
    for y in range(192):
        for x in range(108):
            dx, dy = (x - 53.5) / 54, (y - 95.5) / 96
            px[x, y] = int(255 * strength * min(1, max(0, (dx * dx * 1.3 + dy * dy * 0.6) - 0.25) / 0.9))
    m = small.resize((W, H), Image.BICUBIC)
    return Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), canvas, m)


def place_collage_cinema(canvas, main_path, back_path):
    """Main photo full width, flush with the bottom edge. The second photo sits
    behind the text area and melts into the main one through a long soft
    cross-fade: no lines, no black band at the bottom."""
    main = _fit_w(load_srgb(main_path), W)
    back = _fit_w(load_srgb(back_path), W)
    back = Image.eval(back, lambda v: int(v * 0.72))          # keep the main photo dominant
    top_main = H - main.height
    back_bottom = top_main + COLLAGE_BLEND
    top_back = back_bottom - back.height
    if top_back > 0:                                          # short photo: top melts into black
        mb = Image.new("L", back.size, 255); d = ImageDraw.Draw(mb)
        for y in range(min(back.height, 260)):
            d.line([(0, y), (W, y)], fill=int(255 * smoothstep(y / 260)))
        canvas.paste(back, (0, top_back), mb)
    else:
        canvas.paste(back.crop((0, -top_back, W, back.height)), (0, 0))
    mm = Image.new("L", main.size, 255); d = ImageDraw.Draw(mm)
    for y in range(COLLAGE_BLEND):
        d.line([(0, y), (W, y)], fill=int(255 * smoothstep(y / COLLAGE_BLEND) ** 1.2))
    canvas.paste(main, (0, top_main), mm)
    return top_main


def _card(img, w, radius=28, max_ratio=None):
    card = _fit_w(img, w)
    if max_ratio and card.height > w * max_ratio:          # tall (portrait) photo: centre crop
        h = round(w * max_ratio); t = (card.height - h) // 2
        card = card.crop((0, t, w, t + h))
    mask = Image.new("L", (card.width * 3, card.height * 3), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, mask.width - 1, mask.height - 1], radius=radius * 3, fill=255)
    return card, mask.resize(card.size, Image.LANCZOS)


def _shadow(canvas, box, radius=28, blur=34, offset=22, opacity=0.65):
    from PIL import ImageFilter
    sh = Image.new("L", (W, H), 0)
    x0, y0, x1, y1 = box
    ImageDraw.Draw(sh).rounded_rectangle([x0, y0 + offset, x1, y1 + offset], radius=radius, fill=int(255 * opacity))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    return Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), canvas, sh)


CARD_RADIUS = 28


def collage_backdrop(back_path):
    """Main photo as a dim full-bleed backdrop."""
    back_full = load_srgb(back_path)
    bg = back_full.resize((round(back_full.width * H / back_full.height), H), Image.LANCZOS)
    left = (bg.width - W) // 2
    return Image.eval(bg.crop((left, 0, left + W, H)), lambda v: int(v * 0.30))


def place_collage_cards(canvas, main_path, second_path):
    """Editorial layout: both photos as large rounded cards, staggered
    right/left, over the dim backdrop."""
    a, am = _card(load_srgb(second_path), 640, CARD_RADIUS, max_ratio=0.72)   # upper card, right (detail)
    b, bm = _card(load_srgb(main_path), 820, CARD_RADIUS, max_ratio=0.75)   # lower card, left (main)
    ax, ay = W - a.width - 44, INFO_BOTTOM + 70
    bx = 44
    by = max(H - b.height - 150, ay + a.height - 110)       # pleasant overlap ...
    by = min(by, H - b.height - 110)                        # ... but stay clear of the bottom
    canvas.paste(a, (ax, ay), am)                           # plain rounded cards:
    canvas.paste(b, (bx, by), bm)                           # no glass, no shadows
    return canvas


def build(args):
    canvas = Image.new("RGB", (W, H), (0, 0, 0))
    if getattr(args, "photo2", None) and getattr(args, "collage_style", "cinema") == "cards":
        canvas = collage_backdrop(args.photo)
        canvas = dark_overlay(canvas, INFO_BOTTOM, end=INFO_BOTTOM + 160)
        canvas = place_collage_cards(canvas, args.photo, args.photo2)
    elif getattr(args, "photo2", None):
        top_main = place_collage_cinema(canvas, args.photo, args.photo2)
        canvas = dark_overlay(canvas, top_main, end=min(top_main + 60, INFO_BOTTOM + 300))
        canvas = _vignette(canvas)
    else:
        top, _ = place_photo(canvas, args.photo, args.zoom, args.focus_x, args.bottom)
        canvas = dark_overlay(canvas, top)

    brand, model = split_title(args.title)
    # brand line
    bf = font_for_cap(F_BRAND, BRAND_CAP_H)
    while text_width(brand.upper(), bf, 3) > TITLE_MAX_W and bf.size > 30:
        bf = ImageFont.truetype(F_BRAND, bf.size - 2)
    draw_text_cap(canvas, (X0, BRAND_CAP_TOP), brand.upper(), bf, (255, 255, 255), tracking=3)
    # model line (silver italic)
    if model:
        mcap = MODEL_CAP_H
        mf = font_for_cap(F_MODEL, mcap)
        while text_width(model.upper(), mf, 2) > TITLE_MAX_W and mcap > 30:
            mcap -= 2; mf = font_for_cap(F_MODEL, mcap)
        layer = silver_text_layer(model.upper(), mf, mcap, 2)
        canvas.paste(layer, (X0 - 10, MODEL_CAP_TOP + (MODEL_CAP_H - mcap) - 20), layer)

    # stripe
    d = ImageDraw.Draw(canvas)
    y0, y1 = ROW_TOPS[0], INFO_BOTTOM - 6
    seg = (y1 - y0) / 3
    for i, col in enumerate((BLUE, WHITE, RED)):
        d.rectangle([STRIPE_X, round(y0 + i * seg), STRIPE_X + STRIPE_W - 1, round(y0 + (i + 1) * seg) - 1], fill=col)

    # rows
    lf = ImageFont.truetype(F_LABEL, LABEL_SIZE)
    vf = ImageFont.truetype(F_VALUE, VALUE_SIZE)
    rows = [("Год:", args.year, icon_calendar()),
            ("Пробег:", f"{args.mileage} km", icon_speedometer()),
            ("Цена под ключ:", f"{args.price}₽", icon_tag())]
    for (label, value, icon), top in zip(rows, ROW_TOPS):
        paste_icon(canvas, icon, ICON_X, top + 2)
        draw_text_cap(canvas, (TEXT_X, top + 2), label, lf, (235, 235, 235))
        draw_text_cap(canvas, (TEXT_X, top + 2 + LABEL_TO_VALUE), value, vf, (255, 255, 255))

    srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    canvas.save(args.out, quality=95, subsampling=0, icc_profile=srgb)
    return args.out


def parse_post(text):
    """Extract title/year/mileage/price from a Telegram post (first lines)."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    title = lines[0]
    blob = "\n".join(lines[1:])
    m_year = re.search(r"Год\s*(?:выпуска)?\s*[:\-–]?\s*(\d{4})", blob, re.I)
    m_km = re.search(r"Пробег\s*[:\-–]?\s*([\d’'`\s .,]+?)\s*(?:km|км)\b", blob, re.I)
    m_price = re.search(r"Цена(?:\s+под\s+ключ)?\s*[:\-–]?\s*([\d\s .]+?)\s*(?:₽|руб|р\.|р\b)", blob, re.I)
    missing = [n for n, m in (("Год", m_year), ("Пробег", m_km), ("Цена", m_price)) if not m]
    if missing:
        raise ValueError("нет строк: " + ", ".join(missing))
    norm = lambda s: re.sub(r"[\s ]+", " ", s).strip()
    return title, m_year.group(1), norm(m_km.group(1)), norm(m_price.group(1))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("photo"); p.add_argument("out")
    p.add_argument("--title"); p.add_argument("--year"); p.add_argument("--mileage"); p.add_argument("--price")
    p.add_argument("--post", help="file with the Telegram post text (alternative to the 4 fields)")
    p.add_argument("--zoom", type=float, default=1.0, help=">1 crops the sides to make the bike bigger")
    p.add_argument("--focus-x", type=float, default=0.5, help="horizontal center of the crop, 0..1")
    p.add_argument("--bottom", type=float, default=150,
                   help="gap in px between the photo bottom and the frame bottom (faded to black)")
    a = p.parse_args()
    if a.post:
        a.title, a.year, a.mileage, a.price = parse_post(open(a.post, encoding="utf-8").read())
    print(build(a))
