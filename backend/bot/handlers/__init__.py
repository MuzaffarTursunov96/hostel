from .start import router as start_router
from .root_expiry import router as root_expiry_router

def setup_routers(dp):
    dp.include_router(start_router)
    dp.include_router(root_expiry_router)
