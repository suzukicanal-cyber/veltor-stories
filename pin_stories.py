#!/usr/bin/env python3
"""One-off: keep (pin) in the group's profile every story already published there by the bot,
including the ones whose 24 h have passed (they are in the archive)."""
import asyncio, json, os

from telethon import TelegramClient, functions
from telethon.sessions import StringSession

PEER = json.load(open("config.json"))["publish"]["peer"]


async def main():
    async with TelegramClient(StringSession(os.environ["TG_SESSION"]), int(os.environ["TG_API_ID"]),
                              os.environ["TG_API_HASH"]) as client:
        peer = await client.get_input_entity(PEER)
        ids, offset = [], 0
        while True:
            r = await client(functions.stories.GetStoriesArchiveRequest(peer=peer, offset_id=offset, limit=100))
            got = [s.id for s in r.stories]
            ids += got
            if len(got) < 100:
                break
            offset = got[-1]
        active = await client(functions.stories.GetPeerStoriesRequest(peer=peer))
        ids += [s.id for s in active.stories.stories]
        ids = sorted(set(ids))
        print("stories found:", ids)
        if ids:
            done = await client(functions.stories.TogglePinnedRequest(peer=peer, id=ids, pinned=True))
            print("pinned:", done)


asyncio.run(main())
