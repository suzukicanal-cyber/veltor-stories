#!/usr/bin/env python3
"""VELTOR lead hunter. Runs on GitHub Actions every hour (.github/workflows/leads.yml).

1. Telegram (main source, tg_source.py): a separate "reader" account reads new
   messages in the moto chats it has joined.
2. Optional: public VK posts (newsfeed.search, needs VK_SERVICE_TOKEN), comments
   in watched VK communities and RSS feeds (config.json).
3. Scores every text: buyer intent and import words count up, sellers' ads
   (prices, phones, "в наличии", "привезём") count down.
4. Sends each lead to Telegram as a card: who, where, what they wrote, why it is
   a lead, a link to the message and a ready reply to copy. Nobody is contacted
   automatically: the manager answers from @veltor_kor himself.

The repository is public, so nothing personal is written to it or to the
Actions log: seen.json keeps only hashes and message numbers, the log only counts.

Secrets: TELEGRAM_BOT_TOKEN (the stories bot, delivers the cards),
TG_API_ID + TG_API_HASH + TG_SESSION (reader account, see tg_login.py),
VK_SERVICE_TOKEN (optional).
`python leads/hunter.py --test` sends one sample card to check delivery,
`--find-chats` sends a list of public moto chats the reader could join.
"""
import hashlib, html, json, os, re, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config.json"
SEEN = ROOT / "seen.json"
VK_API = "https://api.vk.com/method/"
VK_V = "5.199"
KEEP_SEEN_DAYS = 30

CHANNEL = "https://t.me/koreamotocycles_veltor"
MANAGER = "https://t.me/veltor_kor"
SITE = "https://veltormotokorea.ru"
PODBOR = "veltormotokorea.ru/podbor/?src="   # quiz on the site; src marks where the client was found

# ---------------------------------------------------------------- scoring

def norm(text):
    return re.sub(r"\s+", " ", (text or "").lower().replace("ё", "е")).strip()

TOPIC = re.compile(
    r"мото|мотик|байк|скутер|мопед|эндуро|питбайк|спортбайк|чоппер|круизер|нейкед|"
    r"\b(honda|хонда|yamaha|ямаха|kawasaki|кавасаки|suzuki|сузуки|ducati|дукати|triumph|триумф|ktm|"
    r"harley|харлей|aprilia|априли|hyosung|хиосунг|vespa|веспа|husqvarna|indian|moto guzzi|mv agusta)\b|"
    r"\b(gold ?wing|голдвинг|africa twin|африка твин|pcx|nmax|xmax|tmax|forza|cbr ?\d*|cb ?\d{3,4}|"
    r"mt-?\d{2}|yzf|ninja|ниндзя|z ?\d{3,4}|gsx\S*|hayabusa|хаябус\w*|vulcan|v-?strom|tenere|tracer|"
    r"rebel|ребел|shadow|steed|intruder|bandit|versys|r ?1250 ?gs|r ?1200 ?gs|s ?1000 ?rr|k ?1600)\b")

KOREA = re.compile(r"\bкоре(я|и|ю|е|йск)")   # \b: "скорее" is not Korea
IMPORT = re.compile(
    r"из япони|с япони|японск\w* аукцион|из сша|из америк|из европ|из-за границ|из за границ|из-за бугра|"
    r"из за бугра|под заказ|пригна|пригон|привез|привоз|растамож|таможн|аукцион|импорт|утильсбор|эптс|сбктс")
INTENT = re.compile(
    r"\bищу\b|\bхочу\b|\bхотел\w*|\bнуж(ен|на|но)\b|\bкуплю\b|\bкупить\b|посовет|подскаж|"
    r"\bкто (возил|пригонял|заказывал|привозил|брал|покупал|занимается|знает)|кто[- ]нибудь|\bкто-то\b|"
    r"сколько (стоит|будет стоить|выйдет|обойдется)|реально ли|стоит ли|есть опыт|через кого|к кому обрат|"
    r"порекоменд|рассматриваю|планирую|мечтаю|присматриваю|выбираю|интересует|"
    r"как (привезти|пригнать|заказать|купить)|где (купить|заказать|найти)|подбер(ите|и)\b")
PRICE_Q = re.compile(r"сколько|цен[аы]|стоимост|бюджет|обойдется|выйдет|дорого")
WHO_Q = re.compile(r"\bкто\b|через кого|к кому|посовет|порекоменд|компани|контор|перекуп")
SELLER = re.compile(
    r"\bпродам\b|\bпродаю\b|\bпрода[ею]тся\b|в наличии|в продаже|\bдоставим\b|\bпривезем\b|\bпригоним\b|"
    r"\bподберем\b|\bвыкуп\w*|наши клиенты|наших клиентов|\bзвоните\b|пишите в (лс|личк|директ|личные)|"
    r"подписывайтесь|подпишись|\bакци[яи]\b|\bскидк|оставьте заявку|оставляйте заявк|заказать у нас|"
    r"наш канал|наш сайт|\bмы (привозим|возим|работаем|доставляем|подбираем|занимаемся)|отзывы клиентов|"
    r"whatsapp|ватсап|выдали|выдача|новому владельцу|новый владелец|\bприбыл[аи]?\b|\bлоты?\b|"
    r"\bот \d[\d\s.,]*\s?(₽|руб|р\b|млн|тыс)|\bцена[:\s]|под ключ от")
PHONE = re.compile(r"(\+7|\b8)[\s\-(]*\d{3}[\s\-)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}")
URL = re.compile(r"https?://|vk\.cc|t\.me/")

BRANDS = ["honda", "yamaha", "kawasaki", "suzuki", "bmw", "ducati", "triumph", "ktm", "harley-davidson",
          "harley", "aprilia", "hyosung", "vespa", "husqvarna", "indian", "хонда", "ямаха", "кавасаки",
          "сузуки", "дукати", "харлей", "триумф"]
MODEL = re.compile(r"\b(" + "|".join(re.escape(b) for b in BRANDS) + r")\b[\s\-]*([a-z0-9][\w\-]*(?:\s[a-z0-9][\w\-]*)?)?")


def score(text, *, from_user=True, import_context=False, topic_context=False):
    """Return (score, reasons) for a text. score < config min_score means "not a lead".
    import_context: import is implied (comments in import communities);
    topic_context: motorcycles are implied (moto chats), import still has to be said."""
    t = norm(text)
    if not t or len(t) < 15:
        return 0, []
    has_topic = bool(TOPIC.search(t)) or import_context or topic_context
    korea = bool(KOREA.search(t))
    imp = bool(IMPORT.search(t)) or import_context
    intents = {m.group(0) for m in INTENT.finditer(t)}
    sellers = {m.group(0) for m in SELLER.finditer(t)}
    if not has_topic or not (korea or imp) or not intents:
        return 0, []
    s, why = 0.0, []
    if korea:
        s += 3; why.append("Корея")
    if imp:
        s += 2 if not korea else 1; why.append("привоз/под заказ")
    s += min(1.5 + (len(intents) - 1), 3.5)
    if PRICE_Q.search(t):
        why.append("спрашивает цену")
    if WHO_Q.search(t):
        why.append("ищет, через кого привезти")
    if not (PRICE_Q.search(t) or WHO_Q.search(t)):
        why.append("хочет купить")
    if "?" in t:
        s += 0.5
    s += 1 if from_user else -2
    s -= 2.5 * len(sellers)
    if PHONE.search(t):
        s -= 2
    if len(URL.findall(t)) >= 2:
        s -= 1
    if len(t) > 1500:
        s -= 1.5
    elif len(t) > 800:
        s -= 0.5
    return round(s, 1), why


def find_model(text):
    m = MODEL.search(norm(text))
    if not m:
        return ""
    words = [m.group(1)] + ([m.group(2)] if m.group(2) else [])
    stop = {"из", "с", "в", "под", "или", "и", "за", "на", "до", "года", "год"}
    out = []
    for w in " ".join(words).split():
        if w in stop:
            break
        out.append(w)
    upper = {"bmw", "ktm", "pcx", "nmax", "xmax", "tmax", "cbr", "gsx", "yzf", "gs", "rr", "vfr", "nc", "mt"}
    nice = [w.upper() if (any(c.isdigit() for c in w) or w in upper) else w.capitalize() for w in out[:3]]
    return " ".join(nice)


def draft_reply(text, model, src="tg"):
    """A short, human first reply. The manager edits it before sending."""
    t = norm(text)
    podbor = PODBOR + src
    price_on = f"на {model}" if model else "под ваш вариант"
    about = f"по {model}" if model else "по моделям"
    wants = model or "мотоцикл"
    if PRICE_Q.search(t):
        return (f"Здравствуйте! Мы как раз привозим мотоциклы из Южной Кореи под ключ. "
                f"Могу посчитать точную цену {price_on} до Москвы — с осмотром на месте до покупки и оформлением ЭПТС. "
                f"Какой год и бюджет рассматриваете? Примеры наших подборов: {CHANNEL}")
    if WHO_Q.search(t):
        return (f"Здравствуйте! Мы VELTOR, возим мотоциклы из Кореи: подбор, живой осмотр с фото и видео "
                f"до покупки, доставка в среднем 45 дней, СБКТС и ЭПТС. Если интересно — подскажу {about}, "
                f"сроки и цену. Заявку можно собрать за минуту: {podbor}")
    return (f"Здравствуйте! Вижу, что ищете {wants}. Мы привозим мотоциклы из Южной Кореи под ключ — "
            f"подберём вариант под ваш бюджет, а перед покупкой покажем его вживую на фото и видео. "
            f"Подсказать по ценам? Подбор за минуту: {podbor}")

# ---------------------------------------------------------------- helpers

def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return default


def key(*parts):
    return hashlib.sha256(":".join(map(str, parts)).encode()).hexdigest()[:16]


def ago(ts):
    mins = max(0, int((time.time() - ts) / 60))
    if mins < 60:
        return f"{mins} мин назад"
    if mins < 48 * 60:
        return f"{mins // 60} ч назад"
    return f"{mins // 1440} дн назад"


def http_json(url, data=None, timeout=60):
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers={"User-Agent": "veltor-leads/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def vk(method, **params):
    params.update(access_token=os.environ["VK_SERVICE_TOKEN"], v=VK_V)
    for attempt in range(3):
        data = http_json(VK_API + method, params)
        err = data.get("error")
        if not err:
            time.sleep(0.35)            # service key: max 3 requests per second
            return data["response"]
        if err.get("error_code") == 6:  # too many requests per second
            time.sleep(1.5)
            continue
        raise RuntimeError(f"VK {method}: {err.get('error_code')} {err.get('error_msg')}")
    raise RuntimeError(f"VK {method}: rate limit")


def names(resp):
    out = {}
    for p in resp.get("profiles", []):
        out[p["id"]] = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
    for g in resp.get("groups", []):
        out[-g["id"]] = g.get("name", "сообщество")
    return out

# ---------------------------------------------------------------- sources

def vk_search(cfg, since):
    """Fresh public posts for every query in config.json."""
    found = {}
    for q in cfg.get("vk_queries", []):
        start_from = None
        for _ in range(2):              # up to 400 posts per query
            params = dict(q=q, count=200, start_time=since, extended=1,
                          fields="first_name,last_name,name,screen_name")
            if start_from:
                params["start_from"] = start_from
            resp = vk("newsfeed.search", **params)
            who = names(resp)
            for p in resp.get("items", []):
                owner, author = p["owner_id"], p.get("from_id", p["owner_id"])
                found[(owner, p["id"])] = {
                    "source": "ВКонтакте", "src": "vk", "id": key("vk", owner, p["id"]),
                    "text": p.get("text", ""), "date": p["date"], "from_user": author > 0,
                    "author": who.get(author, ""), "owner": owner, "author_id": author,
                    "url": f"https://vk.com/wall{owner}_{p['id']}",
                    "profile": f"https://vk.com/id{author}" if author > 0 else "",
                }
            start_from = resp.get("next_from")
            if not start_from:
                break
    return list(found.values())


def vk_comments(cfg, since):
    """Recent comments under the last posts of watched communities (import is implied there)."""
    out = []
    for domain in cfg.get("vk_watch_groups", []):
        try:
            wall = vk("wall.get", domain=domain, count=15)
        except RuntimeError as e:
            print(f"  watch group skipped: {e}")
            continue
        for post in wall.get("items", []):
            if not post.get("comments", {}).get("count") or post["date"] < since - 14 * 86400:
                continue
            owner = post["owner_id"]
            resp = vk("wall.getComments", owner_id=owner, post_id=post["id"], count=100, sort="desc",
                      extended=1, fields="first_name,last_name,name")
            who = names(resp)
            for c in resp.get("items", []):
                if c.get("date", 0) < since or c.get("from_id", 0) <= 0:
                    continue
                out.append({
                    "source": "ВК, комментарий", "src": "vk", "id": key("vkc", owner, c["id"]),
                    "text": c.get("text", ""), "date": c["date"], "from_user": True, "import_context": True,
                    "author": who.get(c["from_id"], ""), "owner": owner, "author_id": c["from_id"],
                    "url": f"https://vk.com/wall{owner}_{post['id']}?reply={c['id']}",
                    "profile": f"https://vk.com/id{c['from_id']}",
                })
    return out


def rss(cfg, since):
    out = []
    for feed in cfg.get("rss_feeds", []):
        try:
            req = urllib.request.Request(feed, headers={"User-Agent": "veltor-leads/1.0"})
            root = ET.fromstring(urllib.request.urlopen(req, timeout=60).read())
        except Exception as e:  # a broken feed must not stop the rest
            print(f"  rss skipped: {type(e).__name__}")
            continue
        for item in root.iter("item"):
            title, desc = item.findtext("title", ""), item.findtext("description", "")
            link = item.findtext("link", "")
            text = re.sub(r"<[^>]+>", " ", f"{title}. {desc}")
            out.append({"source": urllib.parse.urlparse(feed).netloc, "src": "site", "id": key("rss", link),
                        "text": html.unescape(text), "date": int(time.time()), "from_user": True,
                        "author": "", "owner": 0, "author_id": 0, "url": link, "profile": ""})
    return out

# ---------------------------------------------------------------- telegram

def tg_send(chat_id, text, buttons):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": "true",
            "reply_markup": json.dumps({"inline_keyboard": [buttons]}, ensure_ascii=False)}
    resp = http_json(f"https://api.telegram.org/bot{token}/sendMessage", data)
    if not resp.get("ok"):
        raise RuntimeError(f"telegram: {resp.get('description')}")


def card(lead, cfg):
    e = html.escape
    hot = lead["score"] >= cfg.get("hot_score", 5)
    excerpt = re.sub(r"\s+", " ", lead["text"]).strip()
    if len(excerpt) > 500:
        excerpt = excerpt[:500].rsplit(" ", 1)[0] + "…"
    lines = [f"{'🔥 Горячий' if hot else '🟡 Тёплый'} лид · {e(lead['source'])} · {ago(lead['date'])}"]
    if lead.get("author"):
        lines.append(f"👤 {e(lead['author'])}")
    lines.append(f"💬 «{e(excerpt)}»")
    if lead.get("model"):
        lines.append(f"🏍 {e(lead['model'])}")
    lines.append(f"Почему лид: {e(', '.join(lead['why']))}")
    lines.append("")
    lines.append("✍️ Черновик ответа (нажмите, чтобы скопировать):")
    lines.append(f"<code>{e(lead['reply'])}</code>")
    buttons = [{"text": "Открыть", "url": lead["url"]}] if lead.get("url") else []
    if lead.get("profile"):
        buttons.append({"text": "Профиль", "url": lead["profile"]})
    return "\n".join(lines), buttons


def deliver(leads, cfg):
    chats = cfg.get("deliver_to_chat_ids", [])
    if not chats:
        print("::warning::leads/config.json: deliver_to_chat_ids is empty, nothing sent")
        return 0
    sent = 0
    for lead in leads:
        text, buttons = card(lead, cfg)
        for chat in chats:
            tg_send(chat, text, buttons)
        sent += 1
        time.sleep(1.1)                 # Telegram: about 1 message per second per chat
    return sent

# ---------------------------------------------------------------- main

def run(cfg, now=None):
    now = int(now or time.time())
    seen = load(SEEN, {"last_run": 0, "ids": {}})
    first = not seen.get("last_run")
    since = now - cfg.get("first_run_hours", 72) * 3600 if first else seen["last_run"] - 2 * 3600

    items = []
    if os.environ.get("TG_SESSION"):
        import tg_source                # needs telethon, installed by the workflow
        seen.setdefault("tg_last", {})
        items += tg_source.collect(cfg, since, seen["tg_last"])
    else:
        print("::warning::TG_SESSION is not set — Telegram chats skipped (see leads/README.md)")
    if os.environ.get("VK_SERVICE_TOKEN"):
        items += vk_search(cfg, since)
        items += vk_comments(cfg, since)
    items += rss(cfg, since)

    ignore = set(cfg.get("vk_ignore_ids", []))
    leads = []
    for it in items:
        if it["id"] in seen["ids"] or it["owner"] in ignore or it["author_id"] in ignore:
            continue
        s, why = score(it["text"], from_user=it["from_user"], import_context=it.get("import_context", False),
                       topic_context=it.get("topic_context", False))
        if s < cfg.get("min_score", 3):
            continue
        it.update(score=s, why=why, model=find_model(it["text"]))
        it["reply"] = draft_reply(it["text"], it["model"], it.get("src", "tg"))
        leads.append(it)
    leads.sort(key=lambda x: (-x["score"], -x["date"]))
    cap = cfg.get("max_cards_per_run", 15)
    send, extra = leads[:cap], leads[cap:]

    sent = deliver(send, cfg) if send else 0
    if extra and cfg.get("deliver_to_chat_ids"):
        lines = [f"Ещё {len(extra)} лидов с баллом пониже:"]
        for it in extra[:20]:
            short = re.sub(r"\s+", " ", it["text"]).strip()[:90]
            lines.append(f"• {html.escape(it['source'])}: «{html.escape(short)}…» "
                         f"<a href=\"{html.escape(it['url'])}\">открыть</a>")
        for chat in cfg["deliver_to_chat_ids"]:
            tg_send(chat, "\n".join(lines), [])

    for it in leads:                    # leads over the cap are counted as seen too
        seen["ids"][it["id"]] = now
    cutoff = now - KEEP_SEEN_DAYS * 86400
    seen["ids"] = {k: v for k, v in seen["ids"].items() if v >= cutoff}
    seen["last_run"] = now
    SEEN.write_text(json.dumps(seen, ensure_ascii=False, indent=0), encoding="utf-8")
    # counts only: the Actions log of a public repository is public
    print(f"checked {len(items)} texts, leads {len(leads)}, sent {sent}")


def test_card(cfg):
    sample = ("Всем привет! Хочу Honda CB650R 2021 года, у нас таких почти нет. "
              "Кто-нибудь пригонял мотоцикл из Кореи? Сколько выйдет под ключ до Москвы?")
    s, why = score(sample)
    model = find_model(sample)
    lead = {"source": "ТЕСТ · Мото чат Москва", "text": sample, "date": int(time.time()) - 1800, "score": s,
            "why": why, "model": model, "reply": draft_reply(sample, model, "tg"), "author": "Пример Примеров",
            "url": CHANNEL, "profile": ""}
    deliver([lead], cfg)
    print("test card sent")


def find_chats(cfg):
    """Send a list of public moto chats that the reader account could join."""
    import tg_source
    found = tg_source.search_chats(cfg.get("tg_find_queries", []))
    if not found:
        text = "Публичных мото-чатов по запросам из tg_find_queries не нашлось."
    else:
        lines = ["Публичные мото-чаты, которые нашёл читатель (вступите в нужные с его аккаунта "
                 "или впишите их в tg_join в leads/config.json):", ""]
        for c in found[:40]:
            n = f" · {c['members']:,} уч.".replace(",", " ") if c.get("members") else ""
            lines.append(f"• <a href=\"https://t.me/{c['username']}\">{html.escape(c['title'])}</a>{n}"
                         + (" ✓ уже там" if c.get("joined") else ""))
        text = "\n".join(lines)
    for chat in cfg.get("deliver_to_chat_ids", []):
        tg_send(chat, text[:4000], [])
    print(f"chats found: {len(found)}")


if __name__ == "__main__":
    cfg = load(CONFIG, {})
    if "--test" in sys.argv:
        test_card(cfg)
    elif "--find-chats" in sys.argv:
        find_chats(cfg)
    else:
        run(cfg)
