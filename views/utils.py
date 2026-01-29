import json
import uuid
import platform
import hashlib
from pathlib import Path
import os,sys

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


def resource_path(relative_path: str) -> str:
    """
    Resolve resource path for dev and PyInstaller
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)

    # project root = directory of main_qt.py
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)