#!/usr/bin/env python3
"""Rebuild the story for an already-published post (e.g. after a template change).

Usage (GitHub Actions → "Run workflow" → post_ids): python rebuild_post.py 7713 [7708 ...]

Bots can't read old messages, so the album is fetched by forwarding each of its
messages to the first delivery chat (silently) and deleting the forwarded copy
right away. The new story replaces the old entry in queue.json and is delivered.
"""
import json, sys
from datetime import datetime, timezone

import fetch_and_render as f
import make_story

GROUP_ID = -1003713431807
MAX_ALBUM = 10


FETCH_LOG = []


def fetch_album(first_id, via_chat):
    photos, caption, group = [], None, None
    FETCH_LOG.clear()
    for mid in range(first_id, first_id + MAX_ALBUM):
        try:
            m = f.tg("forwardMessage", chat_id=via_chat, from_chat_id=GROUP_ID,
                     message_id=mid, disable_notification=True)
        except Exception as e:
            print(f"  message {mid}: not available ({e})")
            FETCH_LOG.append({"mid": mid, "error": str(e)[:200]})
            break
        try:
            f.tg("deleteMessage", chat_id=via_chat, message_id=m["message_id"])
        except Exception:
            pass
        # Forwarded copies lose media_group_id; album items share the same original date.
        g = (m.get("forward_origin") or {}).get("date") or m.get("forward_date")
        FETCH_LOG.append({"mid": mid, "date": g, "photo": bool(m.get("photo")),
                          "caption": bool(m.get("caption"))})
        if mid == first_id:
            group = g
        elif g != group:
            break                                   # next post started
        if m.get("photo"):
            photos.append((mid, m["photo"][-1]["file_id"]))
        if m.get("caption"):
            caption = m["caption"]
    return photos, caption


def main(ids):
    queue = f.load(f.QUEUE, [])
    chats = f.load(f.CONFIG, {}).get("deliver_to_chat_ids", [])
    if not chats:
        sys.exit("no delivery chat in config.json")
    f.TMP.mkdir(exist_ok=True); f.SOURCES.mkdir(exist_ok=True); f.STORIES.mkdir(exist_ok=True)
    for pid in ids:
        print(f"post {pid}")
        photos, caption = fetch_album(pid, chats[0])
        print(f"  album: {len(photos)} photos")
        old = next((i for i in queue if str(i["post_id"]) == str(pid)), None)
        if not photos:
            print("  no photos found, skipped"); continue
        if caption:
            title, year, mileage, price = make_story.parse_post(caption)
        elif old:
            title, year, mileage, price = old["title"], old["year"], old["mileage"], old["price"]
        else:
            print("  no text found, skipped"); continue
        src = f.SOURCES / f"{pid}.jpg"
        pick = f.pick_photo(photos, src)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
        out = f.STORIES / f"{stamp}_{pid}_v2.jpg"
        entry = {"post_id": pid, "file": f"stories/{out.name}", **pick,
                 "title": title, "year": year, "mileage": mileage, "price": price,
                 "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "status": "new", "rebuilt": True, "album_photos": len(photos)}
        f.render(entry, out)
        if old:
            queue[queue.index(old)] = entry
        else:
            queue.append(entry)
        print(f"  rebuilt {out.name} ({pick['layout']})")
    f.deliver_pending(queue)
    f.QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main([int(x) for x in " ".join(sys.argv[1:]).replace(",", " ").split()])
