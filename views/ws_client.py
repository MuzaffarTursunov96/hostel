import json
import websocket
import traceback

from PySide6.QtCore import QObject, QThread, Signal


# ==========================
# Worker (runs in background)
# ==========================
class WSWorker(QObject):
    message = Signal(dict)
    error = Signal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self._running = True
        self.ws = None

    def stop(self):
        self._running = False
        try:
            if self.ws:
                self.ws.close()   # 🔥 UNBLOCK recv()
        except Exception:
            pass

    def run(self):
        while self._running:
            try:
                self.ws = websocket.WebSocket()
                self.ws.connect(self.url)

                while self._running:
                    raw = self.ws.recv()
                    if raw:
                        self.message.emit(json.loads(raw))

            except Exception as e:
                if self._running:
                    self.error.emit(str(e))
                # wait before reconnect
                QThread.msleep(1000)

            finally:
                try:
                    if self.ws:
                        self.ws.close()
                except Exception:
                    pass

# ==========================
# Client (used by UI)
# ==========================
class WSClient(QObject):
    event = Signal(dict)

    def __init__(self, url, on_event=None):
        super().__init__()
        self.url = url

        self.thread = QThread()
        self.worker = WSWorker(url)

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.message.connect(self.handle_message)
        self.worker.error.connect(self.handle_error)

        if on_event:
            self.event.connect(on_event)

    def start(self):
        self.thread.start()

    def stop(self):
        if self.worker:
            self.worker.stop()    # 🔥 IMPORTANT

        if self.thread:
            self.thread.quit()
            self.thread.wait()
            self.thread = None

    # ======================
    def handle_message(self, data):
        self.event.emit(data)

    def handle_error(self, error):
        print("WS ERROR:", error)
