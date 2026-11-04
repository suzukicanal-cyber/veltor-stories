# Run once on YOUR computer to create the key (session string) for publishing stories.
#   1) py -m pip install telethon
#   2) py make_session.py
# Enter api_id / api_hash from https://my.telegram.org (API development tools),
# then your phone number and the code Telegram sends you (and the 2FA password if you have one).
# Copy the long line it prints into GitHub → Settings → Secrets → Actions → TG_SESSION.
# Never send this line to anyone: it gives full access to your Telegram account.
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = int(input("api_id: ").strip())
api_hash = input("api_hash: ").strip()
with TelegramClient(StringSession(), api_id, api_hash, device_model="VELTOR stories") as client:
    me = client.get_me()
    print("\nВход выполнен:", me.first_name, f"(@{me.username})" if me.username else "")
    print("\nСкопируйте строку ниже целиком в секрет TG_SESSION:\n")
    print(client.session.save())
    print()
input("Нажмите Enter, чтобы закрыть окно…")
