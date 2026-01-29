import requests

API_URL = "https://hmsuz.com/api"

SESSION = requests.Session()
SESSION.headers.update({
    "Connection": "keep-alive",
    "User-Agent": "HostelManager/1.0"
})

def warmup_api():
    try:
        SESSION.get(f"{API_URL}/health", timeout=(10,20))
    except Exception:
        pass
