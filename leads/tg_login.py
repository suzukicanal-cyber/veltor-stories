"""Connect the reader account. Run ONCE on your own computer (Telegram must open there):

    pip install telethon
    python tg_login.py

It asks for api_id and api_hash (my.telegram.org → API development tools),
the reader's phone number and the code Telegram sends to it, then prints a long
session string. Put that string into the GitHub secret TG_SESSION and never show
it to anyone: it opens the reader account.
"""
import asyncio
import getpass

try:
    from telethon import TelegramClient
    from telethon.sessions import StringSession
except ImportError:
    print("Сначала установите библиотеку:  pip install telethon")
    raise SystemExit(1)


async def main():
    api_id = int(input("api_id: ").strip())
    api_hash = input("api_hash: ").strip()
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.start(
        phone=lambda: input("Номер телефона аккаунта-читателя (+7…): ").strip(),
        code_callback=lambda: input("Код, который пришёл в Telegram: ").strip(),
        password=lambda: getpass.getpass("Облачный пароль (если включён, иначе Enter): "),
    )
    me = await client.get_me()
    if (me.username or "").lower() == "veltor_kor":
        print("\n⚠ Это рабочий аккаунт @veltor_kor. Для чтения чатов нужен отдельный аккаунт-читатель.")
        print("Выйдите из этой сессии в настройках Telegram (Устройства) и запустите скрипт с другим номером.")
        await client.disconnect()
        return
    print(f"\nГотово, вошли как {me.first_name}" + (f" (@{me.username})" if me.username else "") + ".")
    print("Скопируйте строку ниже целиком в секрет TG_SESSION на GitHub и никому её не показывайте:\n")
    print(client.session.save())
    print()
    await client.disconnect()


asyncio.run(main())
