from fastapi import Depends,APIRouter, HTTPException
from datetime import datetime, timedelta
from auth import get_current_user

from db import (get_license_key, 
                update_license_key, 
                activate_trial,
                generate)

router = APIRouter(prefix="/license", tags=["LICENSE"])

import secrets

def generate_license():
    return secrets.token_hex(16).upper()


@router.post("/admin/create-license")
def create_license(is_trial: bool = False, trial_days: int = None, user=Depends(get_current_user)):
    if not user["is_admin"] or int(user["telegram_id"]) not in [1343842535,6220656963]:
        raise HTTPException(403, "Not allowed")

    key = generate_license()
    generate(key, is_trial, trial_days)
    return {"license_key": key}




@router.post("/verify")
def verify_license(license_key: str, device_id: str):
    license = get_license_key(license_key)

    if not license:
        raise HTTPException(403, "Invalid license")

    if not license["is_active"]:
        raise HTTPException(403, "License disabled")

    now = datetime.utcnow()

    # 🔹 Trial activation (first run)
    if license["is_trial"] and not license["expires_at"]:
        expires = now + timedelta(days=license["trial_days"])
        activate_trial(license_key, device_id, expires)

    # 🔹 Expiration check
    if license["expires_at"] and license["expires_at"] < now:
        raise HTTPException(403, "Trial expired")

    # 🔹 Device lock
    if license["device_id"] and license["device_id"] != device_id:
        raise HTTPException(403, "License already used")

    if not license["device_id"]:
        update_license_key(license_key, device_id)

    return {
        "status": "ok",
        "expires_at": license["expires_at"]
    }
