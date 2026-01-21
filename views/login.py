from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame,
    QGraphicsDropShadowEffect, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QPixmap
import requests

from i18n import t

API_URL = "https://hmsuz.com/api"


# =========================
# Worker (background login)
# =========================
class LoginWorker(QObject):
    success = Signal(dict)
    # error = Signal()
    error = Signal(str)


    def __init__(self, username, password):
        super().__init__()
        self.username = username
        self.password = password
        self.session = requests.Session()

    def run(self):
        try:
            r = self.session.post(
                f"{API_URL}/auth/login",
                json={
                    "username": self.username,
                    "password": self.password
                },
                timeout=(10, 30)  # ✅ longer handshake + read
            )

            if r.status_code != 200:
                self.error.emit(r.text)
                return

            self.success.emit(r.json())

        except Exception as e:
            self.error.emit(str(e))



# =========================
# Login Page
# =========================
class LoginPage(QWidget):
    def __init__(self, app, on_success):
        super().__init__()
        self.app = app
        self.on_success = on_success

        self.thread = None
        self.worker = None

        self.build_ui()

    # =========================
    def build_ui(self):
        self.setObjectName("LoginPage")

        # ROOT
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # ===== BACKGROUND IMAGE =====
        self.bg = QLabel(self)
        self.bg.setPixmap(QPixmap("assets/icons/login_bg.jpg"))
        self.bg.setScaledContents(True)
        self.bg.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.bg.lower()

        # ===== DARK OVERLAY =====
        overlay = QFrame(self)
        overlay.setStyleSheet("background-color: rgba(15, 23, 42, 0.55);")

        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setAlignment(Qt.AlignCenter)

        # ===== LOGIN CARD =====
        card = QFrame()
        card.setFixedWidth(380)
        card.setStyleSheet("""
            background-color: rgba(255,255,255,0.98);
            border-radius: 18px;
            padding: 28px;
        """)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 12)
        shadow.setColor(Qt.black)
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignTop)

        # ===== TITLE =====
        title = QLabel("HMS")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 26px;
            font-weight: 800;
            letter-spacing: 2px;
            color: #0F172A;
        """)

        subtitle = QLabel(t("sign_in_to_continue"))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            font-size: 12px;
            color: #64748B;
        """)

       

        # ===== INPUTS =====
        self.username = QLineEdit()
        self.username.setPlaceholderText(t("username"))
        self.username.setFixedHeight(44)

        self.password = QLineEdit()
        self.password.setPlaceholderText(t("password"))
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setFixedHeight(44)

        # ===== BUTTON =====
        self.login_btn = QPushButton(t("login"))
        self.login_btn.setObjectName("LoginButton")
        self.login_btn.setFixedHeight(44)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self.try_login)

        self.login_btn.setStyleSheet("""
            QPushButton#LoginButton {
                background-color: #2563EB;
                color: white;
                font-size: 14px;
                font-weight: 600;
                border-radius: 12px;
                padding: 8px 16px;
            }

            QPushButton#LoginButton:hover {
                background-color: #1D4ED8;
            }

            QPushButton#LoginButton:pressed {
                background-color: #1E40AF;
            }

            QPushButton#LoginButton:disabled {
                background-color: #93C5FD;
                color: white;
            }
            """)


        # ===== ERROR LABEL =====
        self.msg_label = QLabel("")
        self.msg_label.setAlignment(Qt.AlignCenter)
        self.msg_label.setStyleSheet("color:#DC2626; font-size:11px;")

        # ===== LAYOUT =====
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(10)
        layout.addWidget(self.username)
        layout.addWidget(self.password)
        layout.addSpacing(6)
        layout.addWidget(self.login_btn)
        layout.addWidget(self.msg_label)

        overlay_layout.addWidget(card)
        root.addWidget(overlay)

        

    # =========================
    def resizeEvent(self, event):
        self.bg.resize(self.size())
        super().resizeEvent(event)

    # =========================
    def try_login(self):
        username = self.username.text().strip()
        password = self.password.text().strip()

        self.msg_label.setText("")

        if not username or not password:
            self.msg_label.setText(t("invalid_username_or_password"))
            return

        self.login_btn.setEnabled(False)

        self.thread = QThread(self)
        self.worker = LoginWorker(username, password)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.success.connect(self.login_success)
        self.worker.error.connect(self.login_failed)

        self.worker.success.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    # =========================
    def login_success(self, data):
        self.app.access_token = data["access_token"]
        self.app.user_id = data["user_id"]
        self.app.is_admin = data["is_admin"]

        self.app.branch_id = data["branch_id"]

        self.app.telegram_id = data.get("telegram_id")

        self.login_btn.setEnabled(True)
        self.on_success()

    def login_failed(self, msg):
        self.login_btn.setEnabled(True)
        self.msg_label.setText(msg)
