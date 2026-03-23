from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from jose import jwt, JWTError
from security import SECRET_KEY, ALGORITHM


import os
from dotenv import load_dotenv
load_dotenv()
ROOT_TELEGRAM_ID = int(os.getenv("ROOT_TELEGRAM_ID", "1343842535"))


security = HTTPBearer()

def get_current_user(token=Depends(security)):
    try:
        return jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def admin_required(user=Depends(get_current_user)):
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    return user



def is_root_admin(user):
    return (
        user["is_admin"] == 1 and
        user["telegram_id"] == ROOT_TELEGRAM_ID
    )

def is_admin(user):
    return (
        user["is_admin"] == 1
    )
