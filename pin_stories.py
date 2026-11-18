#!/usr/bin/env python3
"""One-off fix (18.11.2026):
 - undo the pin of the 5 OLD stories (22, 24, 34, 93, 94) that the first run changed by mistake;
 - pin only the stories the bot published (since 16.11.2026 13:20 UTC).
Prints every story with its date and pinned state before and after."""
import asyncio, json, os
from datetime import datetime, timezone

from telethon import TelegramClient, functions
from telethon.sessions import StringSession

PEER = json.load(open("config.json"))["publish"]["peer"]
SINCE = datetime(2026, 11, 16, 13, 20, tzinfo=timezone.utc)
UNDO = [22, 24, 34, 93, 94]


async def all_stories(client, peer):
    out, offset = {}, 0
    while True:
        r = await client(functions.stories.GetStoriesArchiveRequest(peer=peer, offset_id=offset, limit=100))
        for s in r.stories:
            out[s.id] = s
        if len(r.stories) < 100:
            break
        offset = r.stories[-1].id
    act = await client(functions.stories.GetPeerStoriesRequest(peer=peer))
    for s in act.stories.stories:
        out.setdefault(s.id, s)
    return out


async def main():
    async with TelegramClient(StringSession(os.environ["TG_SESSION"]), int(os.environ["TG_API_ID"]),
                              os.environ["TG_API_HASH"]) as client:
        peer = await client.get_input_entity(PEER)
        st = await all_stories(client, peer)
        for i in UNDO:
            s = st.get(i); print("old", i, getattr(s, "date", None), "pinned:", getattr(s, "pinned", None))
        ours = sorted(i for i, s in st.items() if getattr(s, "date", None) and s.date >= SINCE)
        print("bot stories:", [(i, st[i].date.isoformat(), getattr(st[i], "pinned", None)) for i in ours])
        r = await client(functions.stories.TogglePinnedRequest(peer=peer, id=UNDO, pinned=False))
        print("unpinned (undo):", r)
        if ours:
            r = await client(functions.stories.TogglePinnedRequest(peer=peer, id=ours, pinned=True))
            print("pinned bot stories:", r)
        st = await all_stories(client, peer)
        print("after: old", [(i, getattr(st.get(i), "pinned", None)) for i in UNDO])
        print("after: bot", [(i, getattr(st[i], "pinned", None)) for i in ours])


asyncio.run(main())
