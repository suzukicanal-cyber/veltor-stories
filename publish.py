#!/usr/bin/env python3
"""Publish a ready VELTOR story to the stories of the Telegram group (button «Опубликовать»).

Bots can't post group stories, so this uses the owner's Telegram account (Telethon,
session string in the TG_SESSION secret; TG_API_ID / TG_API_HASH from my.telegram.org).
The story picture becomes a static MP4 (config publish.seconds, 12 s) with a melody from
music/ and is posted to the group. The message in «Сторисы» is then marked as published.

Usage: python publish.py <post_id>
"""
import asyncio, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

import fetch_and_render as f

ROOT = f.ROOT
MUSIC = ROOT / "music"


def pick_track(post_id):
    tracks = sorted(p for p in MUSIC.glob("*") if p.suffix.lower() in (".mp3", ".m4a", ".aac", ".wav", ".ogg"))
    return tracks[int(post_id) % len(tracks)] if tracks else None


def make_video(image, track, seconds, out, start=0.0):
    """Static picture + melody (faded in/out); silent if there is no melody."""
    fade = 1.2
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(image)]
    if track:
        cmd += ["-ss", str(start), "-i", str(track)]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    cmd += ["-t", str(seconds),
            "-vf", "scale=1080:1920:flags=lanczos,format=yuv420p",
            "-af", f"afade=t=in:d=0.4,afade=t=out:st={seconds - fade}:d={fade}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-tune", "stillimage", "-r", "30",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-movflags", "+faststart", "-shortest", str(out)]
    subprocess.run(cmd, check=True)
    return out


async def post_story(video, seconds, peer_name):
    from telethon import TelegramClient, functions, types
    from telethon.sessions import StringSession
    async with TelegramClient(StringSession(os.environ["TG_SESSION"]), int(os.environ["TG_API_ID"]),
                              os.environ["TG_API_HASH"]) as client:
        peer = await client.get_input_entity(peer_name)
        uploaded = await client.upload_file(str(video))
        media = types.InputMediaUploadedDocument(
            file=uploaded, mime_type="video/mp4",
            attributes=[types.DocumentAttributeVideo(duration=seconds, w=1080, h=1920, supports_streaming=True)])
        await client(functions.stories.SendStoryRequest(
            peer=peer, media=media, privacy_rules=[types.InputPrivacyValueAllowAll()], period=86400))


def mark_message(item, text):
    m = item.get("tg_message")
    if not m:
        return
    try:
        f.tg("editMessageCaption", chat_id=m["chat_id"], message_id=m["message_id"],
             caption=f"{item['title']} — {item['price']}₽\n{text}", reply_markup={"inline_keyboard": []})
    except Exception as e:
        print("could not edit the message:", e)


def main(post_id):
    cfg = f.load(f.CONFIG, {}).get("publish") or {}
    queue = f.load(f.QUEUE, [])
    item = next((i for i in reversed(queue) if str(i["post_id"]) == str(post_id)), None)
    if not item:
        sys.exit(f"post {post_id}: no story in queue.json")
    if item.get("published_at"):
        print("already published", item["published_at"]); mark_message(item, "✅ Опубликовано в сторис группы"); return
    seconds = int(cfg.get("seconds", 12))
    f.TMP.mkdir(exist_ok=True)
    track = pick_track(post_id)
    video = make_video(ROOT / item["file"], track, seconds, f.TMP / f"story_{post_id}.mp4",
                       start=float(cfg.get("music_start", 0)))
    print(f"video {video.name}: {seconds} s, melody: {track.name if track else 'нет (тишина)'}")
    try:
        asyncio.run(post_story(video, seconds, cfg.get("peer", f.CHAT_USERNAME)))
    except Exception as e:
        item["publish_error"] = str(e)[:300]
        f.QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
        mark_message(item, f"⚠️ Не удалось опубликовать: {str(e)[:150]}")
        raise
    item["published_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    item["published_track"] = track.name if track else None
    item.pop("publish_error", None)
    f.QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    mark_message(item, "✅ Опубликовано в сторис группы")
    print("published")


if __name__ == "__main__":
    main(sys.argv[1])
