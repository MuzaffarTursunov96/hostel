from fastapi import FastAPI,WebSocket,Request
from db import init_db,create_admin_if_not_exists

from api import auth, branches, rooms, bookings, debts
from api.dashboard import router as dashboard_router
from api.beds import router as beds_router
from api.payments import router as payments_router
from api.payment_history import router as payment_history_router
from api.active_bookings import router as active_bookings_router
from api.exports import router as exports_router
from api.ws_manager import ws_manager
from api.settings import router as settings_router
from api.customers import router as customer_router
from api.booking_history import router as booking_history_router
from api.root_admin import router as root_admin_router
from api.refunds import router as refund_router
from api.users import router as users_router
from api.admin_reports import router as admin_reports_router


from aiogram.types import Update

from bot.bot import bot
from bot.dispatcher import dp
from bot.handlers import setup_routers




import os
from dotenv import load_dotenv
load_dotenv()
WEBHOOK_URL = os.getenv("WEBHOOK_URL")



app = FastAPI(
    title="Hostel Backend API",
    # root_path="/api"
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)



setup_routers(dp)

# ================= STARTUP =================




# ================= WEBSOCKET =================
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text() 
            msg = await ws.receive_text()
            # keep-alive
            print("📥 WS RECEIVED:", msg)
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



# init_db()
# create_admin_if_not_exists()

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
app.include_router(refund_router)
app.include_router(users_router)
app.include_router(admin_reports_router)
