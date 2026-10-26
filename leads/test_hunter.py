"""Checks the lead filter on typical texts: python leads/test_hunter.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hunter import score, find_model, draft_reply  # noqa: E402

MIN = 3

LEADS = [
    ("Всем привет! Хочу Honda CB650R 2021, кто-нибудь пригонял мотоцикл из Кореи? Сколько выйдет под ключ?", {}),
    ("Подскажите, кто возит мотоциклы из Японии под заказ? Интересует Kawasaki Z900", {}),
    ("Ребят, реально ли привезти скутер Honda PCX из Кореи? В Москве цены космос", {}),
    ("Планирую весной брать BMW R 1250 GS, думаю заказать из Южной Кореи. Есть опыт у кого?", {}),
    ("А сколько будет стоить такой же, но 2022 года?", {"import_context": True}),
    ("Посоветуйте, через кого пригнать байк из-за границы, бюджет до 1 млн", {}),
]
NOT_LEADS = [
    ("Мотоциклы из Кореи под ключ! В наличии и под заказ. Доставим за 45 дней. "
     "Звоните +7 999 123-45-67. Подписывайтесь на наш канал", {"from_user": False}),
    ("Продам Yamaha R1 2015, пригнан из Японии, ЭПТС, цена 950 000", {}),
    ("Скорее бы весна, хочу на мотоцикл", {}),
    ("Хочу заказать косметику из Кореи, подскажите магазин", {}),
    ("Наш клиент забрал Honda Gold Wing из Кореи, выдали новому владельцу. Хотите такой же? Оставьте заявку",
     {"from_user": False}),
    ("Куплю мотоцикл дорого, выкуп за 1 час, пригон из Японии", {}),
    ("Мы привозим мотоциклы из Кореи и Японии. Подберем вариант под ваш бюджет, пишите в личку", {}),
    ("Из Кореи пришёл новый Hyundai Palisade, в наличии, цена от 5 млн", {"from_user": False}),
]


def main():
    bad = 0
    for text, kw in LEADS:
        s, why = score(text, **kw)
        ok = s >= MIN
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} lead   {s:>5}  {why}  | {text[:60]}")
    for text, kw in NOT_LEADS:
        s, why = score(text, **kw)
        ok = s < MIN
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} skip   {s:>5}  | {text[:60]}")
    assert find_model("Хочу Honda CB650R 2021 из Кореи") == "Honda CB650R 2021", find_model("Хочу Honda CB650R 2021 из Кореи")
    assert find_model("скутер Honda PCX из Кореи") == "Honda PCX"
    assert find_model("BMW R 1250 GS из Кореи") == "BMW R 1250"
    assert find_model("ищу мотоцикл из Кореи") == ""
    assert "Kawasaki Z900" in draft_reply("сколько стоит", "Kawasaki Z900")
    print("FAILED:", bad) if bad else print("all good")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
