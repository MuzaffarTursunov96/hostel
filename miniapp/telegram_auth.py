import json
import hashlib
import hmac
from urllib.parse import parse_qsl

BOT_TOKEN = "8532587604:AAGZRp6Bvh5ex3ER9SaBNV7_037Eht162w8"

def verify_telegram_init_data(init_data: str):
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN missing")
        return None

    # Parse query string (URL-decoded ONCE – correct)
    data = dict(parse_qsl(init_data, keep_blank_values=True))
    # print(data,'dataaaa')

    # ❗ REMOVE ONLY hash
    hash_from_tg = data.pop("hash", None)

    if not hash_from_tg:
        print("❌ hash missing")
        return None

    # ✅ KEEP signature in data-check-string
    check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(data.items())
    )

    # ✅ WebApp secret key
    secret_key = hmac.new(
        b"WebAppData",
        BOT_TOKEN.encode(),
        hashlib.sha256
    ).digest()

    calculated_hash = hmac.new(
        secret_key,
        check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    if calculated_hash != hash_from_tg:
        print("❌ hash mismatch")
        # print("TG :", hash_from_tg)
        # print("OUR:", calculated_hash)
        return None

    if "user" not in data:
        print("❌ user missing")
        return None

    user = json.loads(data["user"])

    return {
        "id": user["id"],
        "username": user.get("username"),
        "first_name": user.get("first_name"),
        "language_code": user.get("language_code"),
    }
