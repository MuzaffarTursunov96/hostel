# ws_manager.py
from fastapi import WebSocket
from typing import List

class WSManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, event: dict):
        dead = []

        for ws in self.active:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)

        # cleanup dead sockets
        for ws in dead:
            self.disconnect(ws)

ws_manager = WSManager()
