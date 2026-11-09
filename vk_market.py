#!/usr/bin/env python3
"""Товары ВКонтакте из постов темы «Мото».

Запускается в stories.yml сразу после fetch_and_render.py. Берёт записи queue.json,
у которых ещё нет товара в ВК, и создаёт товар в группе из config.json → "vk_market":
название «Модель, год», цена из поста, до 5 фото (те же, что отобраны для сторис),
описание из поста со строкой «Цена актуальна на ДД.ММ.ГГГГ» — дата публикации поста в Telegram.
Товар кладётся в подборку (по умолчанию «Мотоциклы»).

Секрет GitHub: VK_TOKEN — ключ доступа с правами на товары и фотографии.
Без него шаг просто ничего не делает. Ошибка ВК не ломает сборку сторис.
"""
import json, os, re, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
QUEUE = ROOT / "queue.json"
CONFIG = ROOT / "config.json"
MSK = timezone(timedelta(hours=3))
API_VERSION = "5.199"
MAX_ATTEMPTS = 3          # после стольких ошибок пост больше не пробуем (видно в vk_error)


def load(p, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


class VKError(RuntimeError):
    def __init__(self, err):
        self.code = err.get("error_code")
        super().__init__(f"VK {self.code}: {err.get('error_msg')}")


class VK:
    def __init__(self, token, host="api.vk.com"):
        self.token, self.host = token, host

    def call(self, method, **params):
        params = {k: v for k, v in params.items() if v is not None}
        params.update(access_token=self.token, v=API_VERSION)
        data = urllib.parse.urlencode(params).encode()
        for attempt in range(3):
            req = urllib.request.Request(f"https://{self.host}/method/{method}", data=data)
            with urllib.request.urlopen(req, timeout=60) as r:
                res = json.load(r)
            if "error" in res:
                if res["error"].get("error_code") == 6 and attempt < 2:   # too many requests per second
                    time.sleep(1.5); continue
                raise VKError(res["error"])
            time.sleep(0.4)                                               # stay under 3 req/s
            return res["response"]

    def upload(self, url, path):
        boundary = "----vk" + str(int(time.time() * 1000))
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{Path(path).name}"\r\n'
                f'Content-Type: image/jpeg\r\n\r\n').encode() + Path(path).read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.read().decode()


# ---------- текст товара ----------

def posted_date(item):
    """Дата публикации поста в Telegram (по Москве); у старых записей — время обработки."""
    raw = item.get("posted") or item.get("created")
    return datetime.fromisoformat(raw).astimezone(MSK).strftime("%d.%m.%Y")


def price_number(price):
    return int(re.sub(r"\D", "", price))


def product_name(item):
    name = f"{item['title']}, {item['year']}"
    return name[:100]


def product_description(item):
    """Шапка (год, пробег, цена с датой) + остальной текст поста без строк, которые уже в шапке."""
    lines = (item.get("description") or "").splitlines()
    # шапка поста заканчивается строкой с ценой (… ₽ / руб)
    end = next((i for i, l in enumerate(lines) if re.search(r"\d\s*(₽|руб|р\.)", l)), 4)
    body, blank = [], False
    for l in lines[end + 1:]:
        l = l.strip()
        if re.fullmatch(r"\*\d+", l):          # служебные пометки вида *25
            continue
        if not l:
            blank = bool(body); continue
        if blank:
            body.append("")
        body.append(l); blank = False
    mileage = item["mileage"]
    mileage = mileage if re.search(r"нов|new", mileage, re.I) else f"{mileage} км"
    head = [f"Год: {item['year']}",
            f"Пробег: {mileage}",
            f"Цена под ключ: {item['price']} ₽",
            f"Цена актуальна на {posted_date(item)} и меняется вместе с курсом валют.",
            "Мотоцикл из Южной Кореи под заказ — наличие уточняйте."]
    text = "\n".join(head + ([""] + body if body else []))
    return text[:3800]


def product_photos(item):
    files = item.get("gallery") or [item[k] for k in ("source", "source2") if item.get(k)]
    return [ROOT / f for f in files if (ROOT / f).exists()][:5]          # главное + до 4 доп.


# ---------- ВК ----------

def group_id(vk, cfg):
    if cfg.get("group_id"):
        return int(cfg["group_id"])
    res = vk.call("groups.getById", group_id=cfg["group"])
    groups = res.get("groups", res) if isinstance(res, dict) else res
    return int(groups[0]["id"])


def find_category(node, words):
    """Ищет в дереве категорий первую, чьё название содержит одно из слов."""
    if isinstance(node, dict):
        name = str(node.get("name") or node.get("title") or "").lower()
        if node.get("id") and any(w in name for w in words):
            return int(node["id"])
        for v in node.values():
            if isinstance(v, (dict, list)):
                r = find_category(v, words)
                if r:
                    return r
    elif isinstance(node, list):
        for v in node:
            r = find_category(v, words)
            if r:
                return r
    return None


def category_id(vk, cfg):
    if cfg.get("category_id"):
        return int(cfg["category_id"])
    try:
        cats = vk.call("market.getCategories", count=1000)
        cid = find_category(cats, ["мотоцикл", "мототехник", "мото"]) or find_category(cats, ["транспорт", "авто"])
        if cid:
            print(f"VK: категория товара {cid}")
            return cid
    except VKError as e:
        print(f"VK: не получил категории ({e})")
    return 1


def album_id(vk, gid, title):
    if not title:
        return None
    res = vk.call("market.getAlbums", owner_id=-gid, count=100)
    for a in res.get("items", []):
        if a.get("title", "").strip().lower() == title.lower():
            return a["id"]
    return vk.call("market.addAlbum", owner_id=-gid, title=title)["market_album_id"]


def upload_photo(vk, gid, path, main):
    """Новый способ загрузки фото товара; если ВК его не принимает — прежний."""
    try:
        url = vk.call("market.getProductPhotoUploadServer", group_id=gid)["upload_url"]
        res = vk.call("market.saveProductPhoto", upload_response=vk.upload(url, path))
        return res["photo_id"]
    except VKError as e:
        if e.code not in (3, 5, 15, 27, 100):
            raise
    srv = vk.call("photos.getMarketUploadServer", group_id=gid, main_photo=1 if main else 0)
    up = json.loads(vk.upload(srv["upload_url"], path))
    saved = vk.call("photos.saveMarketPhoto", group_id=gid, **{k: up[k] for k in up if k in (
        "photo", "server", "hash", "crop_data", "crop_hash")})
    return saved[0]["id"]


def bike_key(item):
    """Один и тот же мотоцикл: модель + год + пробег (перевыложенный модератором пост)."""
    return (re.sub(r"\W+", "", item["title"]).lower(), item["year"], re.sub(r"\D", "", item["mileage"]))


def create_product(vk, gid, cat, alb, item, existing=None):
    """Создаёт товар; если этот мотоцикл уже есть в ВК (existing = id товара) — обновляет его."""
    photos = product_photos(item)
    if not photos:
        raise RuntimeError("нет фото")
    ids = [upload_photo(vk, gid, p, main=(n == 0)) for n, p in enumerate(photos)]
    fields = dict(owner_id=-gid, name=product_name(item), description=product_description(item),
                  category_id=cat, price=price_number(item["price"]), main_photo_id=ids[0],
                  photo_ids=",".join(map(str, ids[1:])) or None)
    if existing:
        try:
            vk.call("market.edit", item_id=existing, **fields)
            return existing
        except VKError as e:                    # товар удалили вручную — создаём заново
            print(f"VK: не обновил товар {existing} ({e}), создаю новый")
    item_id = vk.call("market.add", **fields)["market_item_id"]
    if alb:
        vk.call("market.addToAlbum", owner_id=-gid, item_ids=item_id, album_ids=alb)
    return item_id


def main():
    cfg = load(CONFIG, {}).get("vk_market") or {}
    token = os.environ.get("VK_TOKEN", "")
    if not cfg.get("enabled") or not token:
        print("VK: выключено или нет VK_TOKEN — пропускаю"); return 0
    queue = load(QUEUE, [])
    since = cfg.get("since", "")
    todo = [it for it in queue
            if not it.get("vk_item_id") and not it.get("vk_skipped") and it.get("source") and it.get("price")
            and (it.get("posted") or it.get("created", "")) >= since
            and it.get("vk_attempts", 0) < MAX_ATTEMPTS]
    if not todo:
        print("VK: новых товаров нет"); return 0
    vk = VK(token, cfg.get("api_host", "api.vk.com"))
    try:
        gid = group_id(vk, cfg)
        cat = category_id(vk, cfg)
        alb = album_id(vk, gid, cfg.get("album", "Мотоциклы"))
    except Exception as e:
        print(f"VK: не удалось подготовить группу: {e}"); return 0
    # у одного мотоцикла берём только самый свежий пост; товар, уже созданный по старому посту, обновляем
    latest = {}
    for it in queue:
        latest[bike_key(it)] = it if it.get("price") else latest.get(bike_key(it))
    in_vk = {bike_key(it): it["vk_item_id"] for it in queue if it.get("vk_item_id")}
    for it in todo:
        if latest.get(bike_key(it)) is not it:
            it["vk_item_id"] = None; it["vk_skipped"] = "есть более новый пост этого мотоцикла"
    todo = [it for it in todo if not it.get("vk_skipped")]
    limit = int(cfg.get("per_run", 10))                      # не заливать сотни товаров за один запуск
    for item in todo[:limit]:
        try:
            item["vk_item_id"] = create_product(vk, gid, cat, alb, item, in_vk.get(bike_key(item)))
            item.pop("vk_error", None)
            print(f"VK: товар {item['vk_item_id']} — {product_name(item)}")
        except Exception as e:
            item["vk_attempts"] = item.get("vk_attempts", 0) + 1
            item["vk_error"] = str(e)[:300]
            print(f"VK: ошибка для поста {item['post_id']}: {e}")
            if isinstance(e, VKError) and e.code in (5, 15, 27):   # токен не тот — дальше бессмысленно
                break
    QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
