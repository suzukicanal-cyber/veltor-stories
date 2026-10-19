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
STORIES = ROOT / "stories"
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


def load(p, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def main():
    state = load(STATE, {"offset": 0})
    queue = load(QUEUE, [])
    done_ids = {item["post_id"] for item in queue}

    updates = tg("getUpdates", offset=state["offset"], limit=100, timeout=0,
                 allowed_updates=["message", "channel_post", "edited_message"])
    if not updates:
        print("no new updates"); return 0

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
        if m.get("caption") or m.get("text"):
            p["caption"] = m.get("caption") or m.get("text")

    TMP.mkdir(exist_ok=True); STORIES.mkdir(exist_ok=True)
    new_count = 0
    for key, p in sorted(posts.items(), key=lambda kv: kv[1]["first_id"]):
        post_id = p["first_id"]
        if post_id in done_ids or not p["photos"] or not p["caption"]:
            continue
        try:
            title, year, mileage, price = make_story.parse_post(p["caption"])
        except Exception as e:  # not a sale post in the usual format
            print(f"skip post {post_id}: cannot parse ({e})"); continue
        first_photo = sorted(p["photos"])[0][1]
        src = TMP / f"{post_id}.jpg"
        download_photo(first_photo, src)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
        out = STORIES / f"{stamp}_{post_id}.jpg"
        args = type("A", (), dict(photo=str(src), out=str(out), title=title, year=year,
                                  mileage=mileage, price=price, zoom=1.0, focus_x=0.5, bottom=150))
        make_story.build(args)
        queue.append({"post_id": post_id, "file": f"stories/{out.name}", "title": title,
                      "year": year, "mileage": mileage, "price": price,
                      "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                      "status": "new"})
        new_count += 1
        print(f"rendered {out.name}: {title}")

    state["offset"] = updates[-1]["update_id"] + 1
    STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"done: {new_count} new stories")
    return 0


if __name__ == "__main__":
    sys.exit(main())
