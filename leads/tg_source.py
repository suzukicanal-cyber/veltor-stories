"""Telegram source for the lead hunter.

A separate "reader" Telegram account (not @veltor_kor) is joined to moto chats.
Every run it reads the messages that appeared since the previous run in every
group it is a member of and hands them to hunter.py for scoring. It never
writes anything anywhere: the cards are delivered by the stories bot.

Needs TG_API_ID, TG_API_HASH (my.telegram.org) and TG_SESSION (tg_login.py).
"""
import asyncio, hashlib, os


def _key(*parts):
    return hashlib.sha256(":".join(map(str, parts)).encode()).hexdigest()[:16]


async def _connect():
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    client = TelegramClient(StringSession(os.environ["TG_SESSION"]),
                            int(os.environ["TG_API_ID"]), os.environ["TG_API_HASH"])
    await client.connect()
    # never client.start() here: on a dead session it would wait for a code forever
    if not await client.is_user_authorized():
        await client.disconnect()
        raise RuntimeError("TG_SESSION больше не действует: заново выполните leads/tg_login.py")
    return client


async def _join(client, names, limit):
    """Join a few public chats from config (slowly: Telegram limits joins)."""
    from telethon import errors
    from telethon.tl.functions.channels import JoinChannelRequest
    done = 0
    clean = dict.fromkeys(n.strip().replace("https://t.me/", "").lstrip("@").split("/")[0] for n in names)
    for name in clean:
        if done >= limit or not name:
            break
        try:
            ent = await client.get_entity(name)
            if getattr(ent, "left", False):
                await client(JoinChannelRequest(ent))
                done += 1
                await asyncio.sleep(5)
        except errors.FloodWaitError:
            break
        except Exception as e:          # wrong name, private chat, etc.: skip it
            print(f"  join skipped: {type(e).__name__}")


def _link(ent, msg_id):
    from telethon.tl.types import Channel
    if getattr(ent, "username", None):
        return f"https://t.me/{ent.username}/{msg_id}"
    if isinstance(ent, Channel):        # private supergroup: opens for its members
        return f"https://t.me/c/{ent.id}/{msg_id}"
    return ""                           # small basic group: no message links


async def _collect(cfg, since, last):
    from telethon import errors
    from telethon.tl.types import User
    ignore = {u.lower().lstrip("@") for u in cfg.get("tg_ignore_usernames", [])}
    per_chat = cfg.get("tg_max_per_chat", 300)
    out, chats = [], 0
    client = await _connect()
    try:
        await _join(client, cfg.get("tg_join", []), cfg.get("tg_join_per_run", 3))
        async for d in client.iter_dialogs():
            if not d.is_group:          # only chats where people talk, not channels
                continue
            chats += 1
            ck = _key("tgchat", d.id)
            last_id = last.get(ck, 0)
            newest = last_id
            try:
                async for m in client.iter_messages(d.entity, min_id=last_id, limit=per_chat):
                    newest = max(newest, m.id)
                    ts = int(m.date.timestamp())
                    if not last_id and ts < since:     # first look at this chat: recent only
                        break
                    if m.out or m.action or not m.message:
                        continue
                    sender = m.sender or await m.get_sender()
                    if sender is None or getattr(sender, "bot", False):
                        continue
                    uname = getattr(sender, "username", None) or ""
                    if uname.lower() in ignore:
                        continue
                    is_user = isinstance(sender, User)
                    name = " ".join(filter(None, [getattr(sender, "first_name", None),
                                                  getattr(sender, "last_name", None)])) \
                        or getattr(sender, "title", "") or ""
                    if uname:
                        name = f"{name} @{uname}".strip()
                    out.append({
                        "source": f"Telegram · {d.name}", "src": "tg", "id": _key("tg", d.id, m.id),
                        "text": m.message, "date": ts, "from_user": is_user, "topic_context": True,
                        "author": name, "owner": d.id, "author_id": sender.id,
                        "url": _link(d.entity, m.id), "profile": f"https://t.me/{uname}" if uname else "",
                    })
            except errors.FloodWaitError as e:
                if e.seconds > 60:
                    print("  telegram asks to slow down, stopping this run")
                    break
                await asyncio.sleep(e.seconds)
            except (errors.ChannelPrivateError, errors.ChatAdminRequiredError):
                continue
            last[ck] = newest
            await asyncio.sleep(0.5)
    finally:
        await client.disconnect()
    print(f"telegram: {chats} chats read")
    return out


async def _search(queries):
    from telethon.tl.functions.contacts import SearchRequest
    found = {}
    client = await _connect()
    try:
        for q in queries:
            res = await client(SearchRequest(q=q, limit=50))
            for c in res.chats:
                if getattr(c, "megagroup", False) and getattr(c, "username", None):
                    found[c.id] = {"title": c.title, "username": c.username,
                                   "members": getattr(c, "participants_count", None) or 0,
                                   "joined": not getattr(c, "left", True)}
            await asyncio.sleep(2)
    finally:
        await client.disconnect()
    return sorted(found.values(), key=lambda c: -c["members"])


def collect(cfg, since, last):
    """New messages from every group the reader is in. `last` (chat hash → last message id) is updated."""
    return asyncio.run(_collect(cfg, since, last))


def search_chats(queries):
    return asyncio.run(_search(queries))
