import requests

API_URL = "http://127.0.0.1:8000"

def api_get(app, path, params=None):
    return requests.get(
        f"{API_URL}{path}",
        headers={
            "Authorization": f"Bearer {app.access_token}"
        },
        params=params,
        timeout=5
    ).json()

def api_post(app, path, json=None):
    response = requests.post(
        f"{API_URL}{path}",
        headers={
            "Authorization": f"Bearer {app.access_token}"
        },
        json=json,
        timeout=5
    )

    # ❌ HANDLE ERRORS
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", "Request failed")
        except Exception:
            detail = response.text or "Request failed"

        raise Exception(detail)

    # ✅ SUCCESS ONLY
    return response.json()

def api_delete(app, path, params=None):
    r = requests.delete(
        f"{API_URL}{path}",
        headers={"Authorization": f"Bearer {app.access_token}"},
        params=params or {},
        timeout=5
    )
    r.raise_for_status()
    return r.json() if r.content else {}
