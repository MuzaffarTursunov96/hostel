# import time
# import requests
# import json

# API_URL = "https://hmsuz.com/api"

# LOGIN_PAYLOAD = {
#     "username": "admin",
#     "password": "admin123"
# }

# CREATE_ADMIN_PAYLOAD = {
#     "telegram_id": 7080578967,
#     "username": "Asror",          # ← intentionally empty to test
#     "password": "1"
# }

# TIMEOUT = (10, 30)  # connect, read
# SESSION = requests.Session()


# def timed(label, fn):
#     start = time.perf_counter()
#     r = fn()
#     ms = round((time.perf_counter() - start) * 1000, 2)
#     print(f"{label}: {ms} ms (status {r.status_code})")
#     return r


# def ms(sec):
#     return round(sec * 1000, 2)


# def timed_request(label, func):
#     start = time.perf_counter()
#     response = func()
#     elapsed = time.perf_counter() - start
#     print(f"{label}: {ms(elapsed)} ms (status {response.status_code})")
#     return response


# def main():
#     print("\n=== LOGIN ===")

#     login_resp = timed_request(
#         "LOGIN",
#         lambda: SESSION.post(
#             f"{API_URL}/auth/login",
#             json=LOGIN_PAYLOAD,
#             timeout=TIMEOUT
#         )
#     )

#     login_resp.raise_for_status()
#     token = login_resp.json().get("access_token")

#     if not token:
#         print("❌ access_token not found in response")
#         print(login_resp.json())
#         return

#     headers = {
#         "Authorization": f"Bearer {token}"
#     }

#     print("\n=== AFTER LOGIN API CALLS ===")

#     # r = timed(
#     #     "POST /root/admins",
#     #     lambda: SESSION.post(
#     #         f"{API_URL}/root/admins",
#     #         headers=headers,
#     #         json=CREATE_ADMIN_PAYLOAD,
#     #         timeout=TIMEOUT
#     #     )
#     # )

#     # print("STATUS:", r.status_code)
#     # print("RESPONSE BODY:", r.text)

#     r = SESSION.get(
#         f"{API_URL}/root/admins",
#         headers=headers,
#         timeout=TIMEOUT
#     )

#     print("STATUS:", r.status_code)
#     print("RESPONSE:")
#     print(r.json())

#     # branch = timed_request(
#     #     "/branches/",
#     #     lambda: SESSION.get(
#     #         f"{API_URL}/branches/",
#     #         headers=headers,
#     #         timeout=TIMEOUT,
           
#     #     )
#     # )

#     # print(branch.json())
#     # timed_request(
#     #     "/rooms/",
#     #     lambda: SESSION.get(
#     #         f"{API_URL}/rooms/",
#     #         headers=headers,
#     #         timeout=TIMEOUT,
#     #         params={"branch_id":6}
#     #     )
#     # )

#     # timed_request(
#     #     "/health",
#     #     lambda: SESSION.get(
#     #         f"{API_URL}/health",
#     #         timeout=TIMEOUT
#     #     )
#     # )

#     print("\n✅ TEST FINISHED")


# if __name__ == "__main__":
#     main()

import secrets

def generate_license():
    return secrets.token_hex(16).upper()

# example
print(generate_license())
# → A3F91C9E4A1D8B77F8E5C9D2A6B4E901



import uuid
import platform
import hashlib

def get_device_id():
    raw = f"{uuid.getnode()}-{platform.system()}-{platform.machine()}"
    return hashlib.sha256(raw.encode()).hexdigest()



import requests

def check_license(license_key):
    device_id = get_device_id()
    r = requests.post(
        "https://hmsuz.com/api/license/verify",
        params={
            "license_key": license_key,
            "device_id": device_id
        },
        timeout=10
    )

    if r.status_code != 200:
        raise Exception(r.text)



import json
from pathlib import Path

LICENSE_FILE = Path.home() / ".hms_license"

def save_license(key):
    LICENSE_FILE.write_text(json.dumps({"key": key}))

def load_license():
    if LICENSE_FILE.exists():
        return json.loads(LICENSE_FILE.read_text())["key"]
