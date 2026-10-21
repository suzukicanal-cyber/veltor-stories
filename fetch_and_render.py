#!/usr/bin/env python3
"""Runs on GitHub Actions every 2 hours.

1. Pulls new messages for the VELTOR bot (Telegram getUpdates).
2. Keeps only posts in the "Мото" topic of @koreamotocycles_veltor.
3. For each new post: takes the FIRST photo of the album + the 5 lines
   (model, year, mileage, price), renders the story with make_story.py.
4. Adds it to queue.json (status "new") for Claude to send to Metricool.
"""
import json, os, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import make_story

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "state.json"
QUEUE = ROOT / "queue.json"
SKIPPED = ROOT / "skipped.json"   # posts that could not become a story, with the reason
CONFIG = ROOT / "config.json"     # {"deliver_to_chat_ids": [...]}: who receives finished stories
STORIES = ROOT / "stories"
SOURCES = ROOT / "sources"       # original photos, kept so stories can be re-rendered
TMP = ROOT / "tmp"

CHAT_USERNAME = "koreamotocycles_veltor"
TOPIC_ID = 8            # "Мото" topic (message_thread_id)

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}"


def tg(method, **params):
    url = f"{API}/{method}?" + urllib.parse.urlencode(
        {k: json.dumps(v) if isinstance(v, (list, dict)) else v for k, v in params.items()})
    with urllib.request.urlopen(url, timeout=60) as r:
        data = json.load(r)
    if not data.get("ok"):
        raise RuntimeError(f"{method}: {data}")
    return data["result"]


def download_photo(file_id, dest):
    path = tg("getFile", file_id=file_id)["file_path"]
    with urllib.request.urlopen(f"https://api.telegram.org/file/bot{TOKEN}/{path}", timeout=120) as r:
        dest.write_bytes(r.read())


MIN_TOP_MARGIN = 0.06   # share of photo height that must be free above the bike
MAX_CANDIDATES = 2      # only photos 1-2: later ones are often close-ups or other bikes
PICK_LOG = []           # margins of the photos checked for the last post
DEBUG_DIR = None        # set to a Path to keep every candidate photo


def pick_photo(photos, dest, force_collage=False):
    """Photo 1 alone if the bike has room above it. Otherwise (and when the album
    has a second photo) a card collage: photo 1 as the main lower card and dim
    backdrop, photo 2 as the smaller upper card.
    Saves the photo(s) next to `dest` and returns a dict for queue.json."""
    PICK_LOG.clear()
    cands = []
    for n, (_, file_id) in enumerate(photos[:MAX_CANDIDATES], start=1):
        cand = TMP / f"cand_{n}.jpg"
        download_photo(file_id, cand)
        cands.append(cand)
        if DEBUG_DIR:
            DEBUG_DIR.mkdir(exist_ok=True)
            (DEBUG_DIR / f"{dest.stem}_photo{n}.jpg").write_bytes(cand.read_bytes())
        if n == 1 and not force_collage:
            margin = make_story.top_margin_ratio(cand)
            print(f"  photo 1: top margin {margin:.2f}")
            PICK_LOG.append({"photo": 1, "margin": round(margin, 3)})
            if margin >= MIN_TOP_MARGIN:
                break
    if len(cands) >= 2:
        dest.write_bytes(cands[0].read_bytes())               # photo 1: main lower card + backdrop
        dest2 = dest.with_name(f"{dest.stem}_2{dest.suffix}")
        dest2.write_bytes(cands[1].read_bytes())              # photo 2: upper card
        return {"layout": "collage", "photo_no": [1, 2],
                "source": f"sources/{dest.name}", "source2": f"sources/{dest2.name}"}
    dest.write_bytes(cands[0].read_bytes())
    return {"layout": "single", "photo_no": 1, "source": f"sources/{dest.name}"}


def render(entry, out):
    """Build the story image for a queue entry (single photo or collage)."""
    args = type("A", (), dict(photo=str(ROOT / entry["source"]), out=str(out),
                              photo2=str(ROOT / entry["source2"]) if entry.get("source2") else None,
                              collage_style="cards", title=entry["title"], year=entry["year"],
                              mileage=entry["mileage"], price=entry["price"],
                              zoom=1.0, focus_x=0.5, bottom=150))
    make_story.build(args)


def send_story(chat_id, path, caption):
    """Send the story as a FILE (sendDocument) so Telegram keeps full 1080x1920 quality."""
    boundary = "----veltor" + str(int(time.time() * 1000))
    parts = []
    for name, value in (("chat_id", str(chat_id)), ("caption", caption)):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="document"; '
                  f'filename="{Path(path).name}"\r\nContent-Type: image/jpeg\r\n\r\n').encode())
    parts.append(Path(path).read_bytes())
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    req = urllib.request.Request(f"{API}/sendDocument", data=b"".join(parts),
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    if not data.get("ok"):
        raise RuntimeError(data)


def deliver_pending(queue):
    """Send every story not yet delivered to the Telegram chats in config.json."""
    chats = load(CONFIG, {}).get("deliver_to_chat_ids", [])
    for item in queue:
        if item.get("status") != "new" or not chats:
            continue
        caption = f"{item['title']} — {item['price']}₽\nГотово для сторис: сохраните файл, добавьте музыку и опубликуйте."
        try:
            for chat in chats:
                send_story(chat, ROOT / item["file"], caption)
            item["status"] = "delivered"
            item["delivered_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            item.pop("last_error", None)
            print(f"delivered {item['file']}")
        except Exception as e:
            item["last_error"] = str(e)[:300]
            print(f"delivery failed for {item['file']}: {e}")


def load(p, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def main():
    state = load(STATE, {"offset": 0})
    queue = load(QUEUE, [])
    done_ids = {item["post_id"] for item in queue}

    updates = tg("getUpdates", offset=state["offset"], limit=100, timeout=0,
                 allowed_updates=["message", "channel_post", "edited_message"])
    if not updates:
        print("no new updates")
        deliver_pending(queue)          # retry earlier failed deliveries, if any
        QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0

    # group album parts (media_group_id) together
    posts = {}
    for u in updates:
        m = u.get("message") or u.get("channel_post") or u.get("edited_message")
        if not m:
            continue
        chat = m.get("chat", {})
        if chat.get("username", "").lower() != CHAT_USERNAME or m.get("message_thread_id") != TOPIC_ID:
            continue
        key = m.get("media_group_id") or f"single-{m['message_id']}"
        p = posts.setdefault(key, {"photos": [], "caption": None, "first_id": m["message_id"]})
        p["first_id"] = min(p["first_id"], m["message_id"])
        if m.get("photo"):
            p["photos"].append((m["message_id"], m["photo"][-1]["file_id"]))  # largest size
        doc = m.get("document") or {}
        if str(doc.get("mime_type", "")).startswith("image/"):          # photo sent "as file"
            p["photos"].append((m["message_id"], doc["file_id"]))
        if m.get("caption") or m.get("text"):
            p["caption"] = m.get("caption") or m.get("text")

    # Text sent as a separate message right after a photo album without caption:
    # attach it to that album.
    ordered = sorted(posts.values(), key=lambda p: p["first_id"])
    for i, p in enumerate(ordered):
        if p["photos"] or not p["caption"]:
            continue
        for prev in reversed(ordered[:i]):
            if prev["photos"] and not prev["caption"] and p["first_id"] - prev["first_id"] <= 12:
                prev["caption"] = p["caption"]; p["caption"] = None
                break

    skipped = load(SKIPPED, [])
    def skip(post_id, reason, caption):
        print(f"skip post {post_id}: {reason}")
        skipped.append({"post_id": post_id, "reason": reason,
                        "text": (caption or "")[:300],
                        "at": datetime.now(timezone.utc).isoformat(timespec="seconds")})

    TMP.mkdir(exist_ok=True); STORIES.mkdir(exist_ok=True); SOURCES.mkdir(exist_ok=True)
    new_count = 0
    for p in ordered:
        post_id = p["first_id"]
        if post_id in done_ids:
            continue
        if not p["photos"] and not p["caption"]:
            continue                                   # service message, sticker, etc.
        if not p["photos"]:
            skip(post_id, "нет фото (только текст или видео)", p["caption"]); continue
        if not p["caption"]:
            skip(post_id, "нет текста с моделью, годом, пробегом и ценой", None); continue
        try:
            title, year, mileage, price = make_story.parse_post(p["caption"])
        except Exception as e:  # not a sale post in the usual format
            skip(post_id, f"не распознан текст ({e})", p["caption"]); continue
        src = SOURCES / f"{post_id}.jpg"
        pick = pick_photo(sorted(p["photos"]), src)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
        out = STORIES / f"{stamp}_{post_id}.jpg"
        entry = {"post_id": post_id, "file": f"stories/{out.name}", **pick,
                 "title": title, "year": year, "mileage": mileage, "price": price,
                 "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "status": "new"}
        render(entry, out)
        queue.append(entry)
        new_count += 1
        print(f"rendered {out.name}: {title}")

    deliver_pending(queue)
    state["offset"] = updates[-1]["update_id"] + 1
    STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    SKIPPED.write_text(json.dumps(skipped[-200:], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"done: {new_count} new stories")
    return 0


if __name__ == "__main__":
    sys.exit(main())
