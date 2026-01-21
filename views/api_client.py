import requests

API_URL = "https://hmsuz.com/api"

# ✅ ONE shared session for whole app
SESSION = requests.Session()
TIMEOUT = (10, 30)  # connect, read


def api_get(app, path, params=None):
    if not getattr(app, "access_token", None):
        raise Exception("User is not logged in")

    response = SESSION.get(
        f"{API_URL}{path}",
        headers={
            "Authorization": f"Bearer {app.access_token}"
        },
        params=params,
        timeout=TIMEOUT
    )

    response.raise_for_status()
    return response.json()


def api_post(app, path, json=None):
    if not getattr(app, "access_token", None):
        raise Exception("User is not logged in")

    response = SESSION.post(
        f"{API_URL}{path}",
        headers={
            "Authorization": f"Bearer {app.access_token}"
        },
        json=json,
        timeout=TIMEOUT
    )

    response.raise_for_status()
    return response.json()


def api_delete(app, path, params=None):
    if not getattr(app, "access_token", None):
        raise Exception("User is not logged in")

    response = SESSION.delete(
        f"{API_URL}{path}",
        headers={
            "Authorization": f"Bearer {app.access_token}"
        },
        params=params or {},
        timeout=TIMEOUT
    )

    response.raise_for_status()
    return response.json() if response.content else {}
