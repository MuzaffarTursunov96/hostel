from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from typing import List
import os
import uuid
from api.ws_manager import ws_manager

from api.deps import get_current_user
from db import get_customers, delete_passport_image_db, image_path, get_image_paths, select_passport_image, upload_passport_image_db

PASSPORT_DIR = os.path.abspath(
    os.path.join(os.getcwd(), "miniapp", "static", "passports")
)
os.makedirs(PASSPORT_DIR, exist_ok=True)



router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("/")
def list_customers(branch_id: int, user=Depends(get_current_user)):
    return get_customers(branch_id)


@router.post("/{customer_id}/passport-images")
async def upload_passport_images(
    customer_id: int,
    files: List[UploadFile] = File(None),  # ✅ FIX HERE
    user=Depends(get_current_user)
    ):
   
    if not files:
        raise HTTPException(400, "No files uploaded")

    if len(files) > 4:
        raise HTTPException(400, "Maximum 4 images allowed")


    
    existing_count = upload_passport_image_db(customer_id)

    if existing_count + len(files) > 4:
        raise HTTPException(
            400,
            f"Customer already has {existing_count} images, max total is 4"
        )

    saved = []

    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            continue

        ext = os.path.splitext(file.filename)[1].lower()
        filename = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(PASSPORT_DIR, filename)

        with open(path, "wb") as f:
            f.write(file.file.read())

        image_path(customer_id, filename)

        saved.append(filename)


    await ws_manager.broadcast({
        "type": "customers_changed",
        "branch_id": user["branch_id"]
    })

    return {
        "ok": True,
        "saved": len(saved)
    }


@router.get("/{customer_id}/passport-images")
def get_passport_images(
            customer_id: int,
            user=Depends(get_current_user)
        ):
    

    return get_image_paths(customer_id)


@router.delete("/passport-images/{image_id}")
async def delete_passport_image(
    image_id: int,
    user=Depends(get_current_user)
):
    
    row = select_passport_image(image_id)

    if not row:
        raise HTTPException(404, "Image not found")

    image_path = row[0]  # /static/passports/xxx.jpg

    # delete DB row

    delete_passport_image_db(image_id)

    # delete file from disk
    fs_path = image_path.lstrip("/")  # static/passports/xxx.jpg
    if os.path.exists(fs_path):
        os.remove(fs_path)

    await ws_manager.broadcast({
    "type": "customers_changed",
    "branch_id": user["branch_id"]
})


    return {"ok": True}