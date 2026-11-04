#!/usr/bin/env python3
"""Short selling points taken literally from the post description.
Only what the post says: nothing is guessed. Ordered by how much they sell."""
import re

NUM = {"один": 1, "одна": 1, "два": 2, "две": 2, "три": 3, "четыре": 4, "пять": 5}


def _n(word):
    return int(word) if word.isdigit() else NUM.get(word.lower())


def _plural(n, one, few, many):
    return one if n % 10 == 1 and n % 100 != 11 else few if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else many


def _keys(t):
    m = re.search(r"\b(\d|один|одна|два|две|три|четыре)\s+(?:\w+\s+)?ключ", t)
    if m and _n(m.group(1)):
        n = _n(m.group(1)); return f"{n} {_plural(n, 'ключ', 'ключа', 'ключей')}"
    if re.search(r"(?:комплект|оба|все)\s+ключ|ключи\s+в\s+комплект", t):
        return "Все ключи"


def _cases(t):
    m = re.search(r"\b(\d|два|две|три)\s+(?:\w+\s+){0,2}кофр", t)
    if m and _n(m.group(1)):
        n = _n(m.group(1)); return f"{n} {_plural(n, 'кофр', 'кофра', 'кофров')}"
    if "кофр" in t:
        return "Кофры"


def _exhaust(t):
    for brand in ("Akrapovic", "SC-Project", "Termignoni", "Arrow", "Yoshimura", "Austin Racing", "Leovince", "Remus"):
        if brand.lower() in t:
            return f"Выхлоп {brand}"
    if re.search(r"прямоток|спортивн\w* выхлоп|тюнинг\w* выхлоп", t):
        return "Спортивный выхлоп"


RULES = [
    (r"без\s+дтп|безаварийн", "Без ДТП"),
    (r"без\s+(?:\w+\s+и\s+)?падени|не\s+падал", "Без падений"),
    (r"перв\w*\s+владел|1\s*владел|один\s+владел|одного\s+владел", "1 владелец"),
    (r"не\s+крашен|родн\w*\s+(?:краск|окрас)|заводск\w*\s+окрас", "Родная краска"),
    (_keys, None),
    (r"гаранти", "На гарантии"),
    (r"сервисн\w*\s+книж", "Сервисная книжка"),
    (r"(?:свеж|пройден|сделан)\w*\s+то\b|\bто\s+(?:пройден|сделан)", "Свежее ТО"),
    (r"обслуживал|обслужен", "Обслуживался"),
    (r"нов\w*\s+(?:шин|резин|покрышк)|(?:шины|резина)\s+нов", "Новые шины"),
    (r"карбон", "Карбоновые детали"),
    (r"плёнк|пленк|\bppf\b", "Защитная плёнка"),
    (_cases, None),
    (_exhaust, None),
    (r"quick\s*shift|квикшифт|квик\s*шифт", "Квикшифтер"),
    (r"круиз", "Круиз-контроль"),
    (r"подогрев\w*\s+(?:руч|грип)", "Подогрев ручек"),
    (r"подогрев\w*\s+сид", "Подогрев сидений"),
    (r"(?:видео)?регистратор", "Видеорегистратор"),
    (r"навигатор|навигаци", "Навигатор"),
    (r"беспроводн\w*\s+зарядк", "Беспроводная зарядка"),
    (r"\busb\b", "USB-порт"),
    (r"слайдер", "Слайдеры"),
    (r"защит\w*\s+(?:двигат|мотор|радиат|бака|рамы|рук)|дуг", "Защита"),
    (r"центральн\w*\s+подножк", "Центральная подножка"),
    (r"(?:высок|туристич)\w*\s+(?:стекл|ветров)", "Туристическое стекло"),
    (r"без\s+вложений", "Без вложений"),
]


def extract(text):
    t = (text or "").lower()
    out = []
    for rule, label in RULES:
        got = rule(t) if callable(rule) else (label if re.search(rule, t) else None)
        if got and got not in out:
            out.append(got)
    # "… в комплекте" taken as written, if short
    for m in re.finditer(r"([а-яa-z0-9][а-яa-z0-9 \-]{2,24}?)\s+в\s+комплекте", t):
        s = m.group(1).strip(); s = s[0].upper() + s[1:] + " в комплекте"
        if len(s) <= 26 and not any(s.lower().startswith(o.lower().split()[0]) for o in out):
            out.append(s)
    return out
