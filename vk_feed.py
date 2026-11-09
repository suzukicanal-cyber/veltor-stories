#!/usr/bin/env python3
"""YML-файл с товарами для группы ВКонтакте из постов темы «Мото».

Запускается в stories.yml после сборки сторис. Берёт из queue.json посты за последние
N дней (config.json → "vk_feed".days), у одного мотоцикла — только самый свежий пост
(модератор перевыкладывает исправленные карточки), и пишет vk/moto.yml.

Ссылка для ВК («Бизнес-инструменты» → «Добавить товар» → «Из файла» → ссылка):
https://raw.githubusercontent.com/suzukicanal-cyber/veltor-stories/main/vk/moto.yml

У товара постоянный id (от модели, года и пробега), поэтому повторная загрузка
того же мотоцикла не должна плодить дубли. В описании — «Цена актуальна на ДД.ММ.ГГГГ»,
дата публикации поста в Telegram.
"""
import json, re, sys, zlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
QUEUE = ROOT / "queue.json"
CONFIG = ROOT / "config.json"
MSK = timezone(timedelta(hours=3))
RAW = "https://raw.githubusercontent.com/suzukicanal-cyber/veltor-stories/main/"
POST_URL = "https://t.me/koreamotocycles_veltor/{}"


def load(p, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def posted(item):
    """Когда пост появился в Telegram; у старых записей — время обработки (те же минуты)."""
    return datetime.fromisoformat(item.get("posted") or item["created"])


def bike_key(item):
    return (re.sub(r"\W+", "", item["title"]).lower(), item["year"], re.sub(r"\D", "", item["mileage"]))


def offer_id(item):
    return str(zlib.crc32("|".join(bike_key(item)).encode()))


def mileage_text(item):
    m = item["mileage"]
    return m if re.search(r"нов|new", m, re.I) else f"{m} км"


def clean(text):
    """Без эмодзи, HTML и управляющих символов — ВК просит чистый текст."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[\U00010000-\U0010FFFF☀-➿️‍]", "", text)
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)


def description(item):
    """Шапка (год, пробег, цена с датой) + остальной текст поста без строк, которые уже в шапке."""
    lines = (item.get("description") or "").splitlines()
    end = next((i for i, l in enumerate(lines) if re.search(r"\d\s*(₽|руб|р\.)", l)), 4)
    body, blank = [], False
    for l in lines[end + 1:]:
        l = clean(l).strip()
        if re.fullmatch(r"\*\d+", l):          # служебные пометки вида *25
            continue
        if not l:
            blank = bool(body); continue
        if blank:
            body.append("")
        body.append(l); blank = False
    head = [f"Год: {item['year']}",
            f"Пробег: {mileage_text(item)}",
            f"Цена под ключ: {item['price']} ₽",
            f"Цена актуальна на {posted(item).astimezone(MSK):%d.%m.%Y} и меняется вместе с курсом валют.",
            "Мотоцикл из Южной Кореи под заказ — наличие уточняйте."]
    return "\n".join(head + ([""] + body if body else []))[:3800]


def pictures(item):
    files = item.get("gallery") or [item[k] for k in ("source", "source2") if item.get(k)]
    return [RAW + f for f in files if (ROOT / f).exists()][:5]


def build(queue, days, category, now=None):
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    latest = {}
    for it in queue:                                  # queue идёт по порядку — последний пост мотоцикла побеждает
        if it.get("price") and it.get("source") and it.get("kind") != "auto":   # только мотоциклы
            latest[bike_key(it)] = it
    items = sorted((it for it in latest.values() if posted(it) >= since), key=posted, reverse=True)
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<yml_catalog date="{now.astimezone(MSK):%Y-%m-%dT%H:%M%z}">',
           "<shop>", "<name>VELTOR</name>", "<company>VELTOR</company>",
           "<url>https://veltormotokorea.ru</url>",
           '<currencies><currency id="RUR" rate="1"/></currencies>',
           f'<categories><category id="1">{escape(category)}</category></categories>', "<offers>"]
    count = 0
    for it in items:
        pics = pictures(it)
        if not pics:
            continue                                  # ВК пропускает товары без фото
        out += [f'<offer id="{offer_id(it)}" available="true">',
                f"<name>{escape(clean(it['title']).strip()[:90] + ', ' + it['year'])}</name>",
                f"<url>{POST_URL.format(it['post_id'])}</url>",
                f"<price>{int(re.sub(r'[^0-9]', '', it['price']))}</price>",
                "<currencyId>RUR</currencyId>", "<categoryId>1</categoryId>",
                *[f"<picture>{escape(p)}</picture>" for p in pics],
                f"<description>{escape(description(it))}</description>",
                f'<param name="Год">{escape(it["year"])}</param>',
                f'<param name="Пробег">{escape(mileage_text(it))}</param>',
                "</offer>"]
        count += 1
    out += ["</offers>", "</shop>", "</yml_catalog>", ""]
    return "\n".join(out), count


def main():
    cfg = load(CONFIG, {}).get("vk_feed") or {}
    if not cfg:
        print("VK feed: выключен"); return 0
    xml, count = build(load(QUEUE, []), int(cfg.get("days", 14)), cfg.get("category", "Мотоциклы"))
    path = ROOT / cfg.get("file", "vk/moto.yml")
    path.parent.mkdir(exist_ok=True)
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    # дата файла меняется каждый запуск — не коммитим, если сами товары не поменялись
    strip = lambda s: re.sub(r'<yml_catalog date="[^"]*">', "", s)
    if strip(old) != strip(xml):
        path.write_text(xml, encoding="utf-8")
    print(f"VK feed: {count} мотоциклов в {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
