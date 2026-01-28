import json
import uuid
import platform
import hashlib
from pathlib import Path

LICENSE_FILE = Path.home() / ".hms_license"


def get_device_id():
    raw = f"{uuid.getnode()}-{platform.system()}-{platform.machine()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def save_license(key: str):
    LICENSE_FILE.write_text(json.dumps({"key": key}))


def load_license():
    if LICENSE_FILE.exists():
        return json.loads(LICENSE_FILE.read_text()).get("key")
    return None

