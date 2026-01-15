from fastapi import FastAPI,WebSocket,Request
from db import init_db, create_admin_if_not_exists

from backend.api import auth, branches, rooms, bookings, debts
from backend.api.dashboard import router as dashboard_router
from backend.api.beds import router as beds_router
from backend.api.payments import router as payments_router
from backend.api.payment_history import router as payment_history_router
from backend.api.active_bookings import router as active_bookings_router
from backend.api.exports import router as exports_router
from backend.api.ws_manager import ws_manager
from backend.api.settings import router as settings_router
from backend.api.customers import router as customer_router
from backend.api.booking_history import router as booking_history_router
from backend.api.root_admin import router as root_admin_router


from aiogram.types import Update

from backend.bot.bot import bot
from backend.bot.dispatcher import dp
from backend.bot.handlers import setup_routers




import os
from dotenv import load_dotenv
load_dotenv()
# WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_URL = 'https://57430a7a9920.ngrok-free.app'



app = FastAPI(title="Hostel Backend API")


setup_routers(dp)

# ================= STARTUP =================
@app.on_event("startup")
async def on_startup():
    # always reset webhook (safe)
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)


# ================= WEBSOCKET =================
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keep-alive
    except Exception:
        pass
    finally:
        ws_manager.disconnect(ws)



# ================= TELEGRAM WEBHOOK =================
@app.post("/tg/webhook")
async def telegram_webhook(request: Request):
    update = Update.model_validate(await request.json())
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.get("/health")
def health():
    return {"ok": True}



init_db()
create_admin_if_not_exists()

app.include_router(auth.router)
app.include_router(branches.router)
app.include_router(rooms.router)
app.include_router(bookings.router)
app.include_router(debts.router)
app.include_router(dashboard_router)
app.include_router(beds_router)
app.include_router(payments_router)
app.include_router(payment_history_router)
app.include_router(active_bookings_router)
app.include_router(exports_router)
app.include_router(settings_router)
app.include_router(customer_router)
app.include_router(booking_history_router)
app.include_router(root_admin_router)
