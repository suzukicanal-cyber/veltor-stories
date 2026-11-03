#!/usr/bin/env python3
"""VELTOR guard: always-on helper for the VELTOR Telegram group (runs on the VPS).

Runs under @VELTOR_moderator_bot (its own token, so it never steals updates from
@veltor_stories_bot) and does two things in real time:
  1. deletes "X проголосовал(а) за группу" (boost) notices within seconds;
  2. when a post appears in the "Мото" topic, starts the stories build on GitHub
     right away (instead of waiting for GitHub's unreliable schedule).

Only the Python standard library is used. Settings come from environment
variables (see veltor-guard.env.example):
  BOT_TOKEN       token of @VELTOR_moderator_bot (admin in the group, "Delete messages")
  GITHUB_TOKEN    fine-grained token, repo veltor-stories, permission Actions: read & write
  GROUP_USERNAME  koreamotocycles_veltor
  MOTO_TOPIC_ID   8
"""
import json, os, sys, time, urllib.request, urllib.error

BOT_TOKEN = os.environ["BOT_TOKEN"]
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GROUP = os.environ.get("GROUP_USERNAME", "koreamotocycles_veltor").lower()
TOPIC = int(os.environ.get("MOTO_TOPIC_ID", "8"))
REPO = os.environ.get("GITHUB_REPO", "suzukicanal-cyber/veltor-stories")
WORKFLOW = os.environ.get("GITHUB_WORKFLOW", "stories.yml")
QUIET = 75          # seconds without new photos in the topic before starting a build
MIN_GAP = 240       # never start builds more often than this

API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def log(*a):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), *a, flush=True)


def tg(method, **params):
    data = json.dumps(params).encode()
    req = urllib.request.Request(f"{API}/{method}", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=70) as r:
        res = json.load(r)
    if not res.get("ok"):
        raise RuntimeError(res)
    return res["result"]


def start_build():
    if not GITHUB_TOKEN:
        log("no GITHUB_TOKEN, build not started")
        return False
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW}/dispatches",
        data=json.dumps({"ref": "main"}).encode(), method="POST",
        headers={"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "veltor-guard"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            log("stories build started, HTTP", r.status)
            return True
    except urllib.error.HTTPError as e:
        log("could not start build:", e.code, e.read()[:200])
        return False


def main():
    me = tg("getMe")
    log(f"running as @{me['username']}")
    offset, pending_since, last_build = 0, None, 0.0
    while True:
        try:
            updates = tg("getUpdates", offset=offset, timeout=50,
                         allowed_updates=["message", "edited_message"])
        except Exception as e:
            log("getUpdates failed:", e)
            time.sleep(5)
            continue
        for u in updates:
            offset = u["update_id"] + 1
            m = u.get("message") or u.get("edited_message") or {}
            chat = m.get("chat", {})
            if (chat.get("username") or "").lower() != GROUP:
                continue
            if m.get("boost_added"):
                try:
                    tg("deleteMessage", chat_id=chat["id"], message_id=m["message_id"])
                    log("deleted boost notice", m["message_id"])
                except Exception as e:
                    log("could not delete boost notice", m["message_id"], e)
                continue
            if m.get("message_thread_id") == TOPIC and (m.get("photo") or m.get("caption")):
                pending_since = time.time()
        # an album arrives as several messages: wait until it is complete
        if pending_since and time.time() - pending_since >= QUIET and time.time() - last_build >= MIN_GAP:
            if start_build():
                last_build = time.time()
            pending_since = None


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
