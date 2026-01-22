import time
import requests
import json

API_URL = "https://hmsuz.com/api"

LOGIN_PAYLOAD = {
    "username": "admin",
    "password": "admin123"
}

TIMEOUT = (10, 30)  # connect, read
SESSION = requests.Session()


def ms(sec):
    return round(sec * 1000, 2)


def timed_request(label, func):
    start = time.perf_counter()
    response = func()
    elapsed = time.perf_counter() - start
    print(f"{label}: {ms(elapsed)} ms (status {response.status_code})")
    return response


def main():
    print("\n=== LOGIN ===")

    login_resp = timed_request(
        "LOGIN",
        lambda: SESSION.post(
            f"{API_URL}/auth/login",
            json=LOGIN_PAYLOAD,
            timeout=TIMEOUT
        )
    )

    login_resp.raise_for_status()
    token = login_resp.json().get("access_token")

    if not token:
        print("❌ access_token not found in response")
        print(login_resp.json())
        return

    headers = {
        "Authorization": f"Bearer {token}"
    }

    print("\n=== AFTER LOGIN API CALLS ===")

    branch = timed_request(
        "/branches/",
        lambda: SESSION.get(
            f"{API_URL}/branches/",
            headers=headers,
            timeout=TIMEOUT,
           
        )
    )

    print(branch.json())
    timed_request(
        "/rooms/",
        lambda: SESSION.get(
            f"{API_URL}/rooms/",
            headers=headers,
            timeout=TIMEOUT,
            params={"branch_id":6}
        )
    )

    timed_request(
        "/health",
        lambda: SESSION.get(
            f"{API_URL}/health",
            timeout=TIMEOUT
        )
    )

    print("\n✅ TEST FINISHED")


if __name__ == "__main__":
    main()
