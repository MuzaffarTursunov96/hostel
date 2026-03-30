from .start import router as start_router
from .root_expiry import router as root_expiry_router
from .client_start import router as client_start_router

def setup_routers(dp):
    dp.include_router(start_router)
    dp.include_router(root_expiry_router)


def setup_client_routers(dp):
    dp.include_router(client_start_router)
