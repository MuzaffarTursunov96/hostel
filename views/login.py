from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame,
    QGraphicsDropShadowEffect, QSizePolicy, QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt, QThread, Signal, QObject,QTimer
from PySide6.QtGui import QPixmap,QIcon
from PySide6.QtWidgets import QProgressBar
import json

from .api_session import SESSION, warmup_api

import threading
from .utils import resource_path

from i18n import t

API_URL = "https://hmsuz.com/api"

# 🔥 Shared session (TLS will be reused)

warmup_api()



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
        self.session = SESSION
        # threading.Thread(target=warmup_api, daemon=True).start()

    def run(self):
        try:
            r = self.session.post(
                f"{API_URL}/auth/login",
                json={
                    "username": self.username,
                    "password": self.password
                },
                timeout=(10, 30)
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
        threading.Thread(target=warmup_api, daemon=True).start()

        self.thread = None
        self.worker = None

        self.build_ui()

    def show_alert(self, text: str):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("HMS")
        box.setText(text)
        box.setStandardButtons(QMessageBox.Ok)
        box.setStyleSheet("""
            QMessageBox {
                background: #ffffff;
            }
            QLabel {
                color: #0f172a;
                font-size: 13px;
                min-width: 280px;
            }
            QPushButton {
                background: #2563EB;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 18px;
                min-width: 90px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #1d4ed8;
            }
        """)
        box.exec()

    # =========================
    def build_ui(self):
        self.setObjectName("LoginPage")

        # ROOT
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # ===== BACKGROUND IMAGE =====
        self.bg = QLabel(self)
        self.bg.setPixmap(QPixmap(resource_path("assets/icons/login_bg.jpg")))
        self.bg.setScaledContents(True)
        self.bg.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.bg.lower()

        


        # ===== DARK OVERLAY =====
        overlay = QFrame(self)
        overlay.setStyleSheet("""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 rgba(15, 23, 42, 0.56),
                stop:1 rgba(15, 23, 42, 0.42)
            );
        """)

        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setContentsMargins(20, 20, 20, 20)
        overlay_layout.setAlignment(Qt.AlignCenter)

        # ===== LOGIN CARD =====
        card = QFrame()
        card.setObjectName("LoginCard")
        card.setFixedWidth(460)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(48)
        shadow.setOffset(0, 16)
        shadow.setColor(Qt.black)
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 30, 32, 28)
        layout.setAlignment(Qt.AlignTop)

        # ===== TITLE / SUBTITLE =====
        badge = QLabel("HMS")
        badge.setObjectName("LoginBadge")
        badge.setAlignment(Qt.AlignCenter)

        title = QLabel(t("welcome_back"))
        title.setObjectName("LoginTitle")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel(t("sign_in_to_continue"))
        subtitle.setObjectName("LoginSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)

        self.login_hint = QLabel(t("login_use_username_password"))
        self.login_hint.setObjectName("LoginHint")
        self.login_hint.setAlignment(Qt.AlignCenter)


        # ===== INPUTS =====
        # ===== INPUTS =====
        self.username = QLineEdit()
        self.username.setObjectName("LoginInput")
        self.username.setPlaceholderText(t("username"))
        self.username.setFixedHeight(50)
        self.username.addAction(
            QIcon(resource_path("assets/icons/user.png")),
            QLineEdit.LeadingPosition
        )
        self.username.returnPressed.connect(self.try_login)

        self.password = QLineEdit()
        self.password.setObjectName("LoginInput")
        self.password.setPlaceholderText(t("password"))
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setFixedHeight(50)
        self.password.addAction(
            QIcon(resource_path("assets/icons/locked.png")),
            QLineEdit.LeadingPosition
        )
        self.password.returnPressed.connect(self.try_login)

        self.show_password = QCheckBox(t("show_password"))
        self.show_password.setObjectName("ShowPassword")
        self.show_password.stateChanged.connect(self.toggle_password_visibility)

        controls_row = QHBoxLayout()
        controls_row.setContentsMargins(2, 0, 2, 0)
        controls_row.addWidget(self.show_password, 0, Qt.AlignLeft)
        controls_row.addStretch(1)


        # ===== BUTTON =====
        self.login_btn = QPushButton(t("login"))
        self.login_btn.setObjectName("LoginButton")
        self.login_btn.setFixedHeight(52)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self.try_login)


        # ===== SPINNER =====
        self.spinner = QProgressBar()
        self.spinner.setRange(0, 0)          # indeterminate
        self.spinner.setFixedHeight(6)
        self.spinner.setTextVisible(False)
        self.spinner.hide()

        self.spinner.setStyleSheet("""
        QProgressBar {
            border: none;
            background-color: #E5E7EB;
            border-radius: 3px;
        }
        QProgressBar::chunk {
            background-color: #2563EB;
            border-radius: 3px;
        }
        """)


        # ===== LAYOUT =====
        layout.addWidget(badge, 0, Qt.AlignHCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.login_hint)
        layout.addSpacing(6)
        layout.addWidget(self.username)
        layout.addWidget(self.password)
        layout.addLayout(controls_row)
        layout.addSpacing(6)
        layout.addWidget(self.login_btn)
        layout.addWidget(self.spinner)

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

        if not username or not password:
            self.show_alert(t("invalid_username_or_password"))
            return

        self.login_btn.setEnabled(False)
        self.spinner.show()


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
        self.username.setEnabled(False)
        self.password.setEnabled(False)
        self.show_password.setEnabled(False)

    # =========================
    def login_success(self, data):
        self.app.access_token = data["access_token"]
        self.app.user_id = data["user_id"]
        self.app.is_admin = data["is_admin"]

        self.app.branch_id = data["branch_id"]

        self.app.telegram_id = data.get("telegram_id")

        QTimer.singleShot(2500, self._finish_login)
        # self.spinner.hide()
        # self.login_btn.setEnabled(True)
        # self.on_success()

    def _finish_login(self):
        self.spinner.hide()              # hide spinner FIRST
        self.login_btn.setEnabled(True)
        self.username.setEnabled(True)
        self.password.setEnabled(True)
        self.show_password.setEnabled(True)
        self.on_success()                # THEN rebuild UI



    def login_failed(self, msg):
        self.spinner.hide()
        self.login_btn.setEnabled(True)
        self.username.setEnabled(True)
        self.password.setEnabled(True)
        self.show_password.setEnabled(True)

        pretty = msg
        try:
            data = json.loads(msg)
            pretty = data.get("detail") or data.get("error") or msg
        except Exception:
            pass

        # Normalize wrong-credentials backend texts to localized UI text
        p = str(pretty).lower()
        if (
            "invalid credentials" in p
            or "неверный логин" in p
            or "login yoki parol" in p
        ):
            pretty = t("invalid_username_or_password")

        self.show_alert(pretty)

    def toggle_password_visibility(self):
        if self.show_password.isChecked():
            self.password.setEchoMode(QLineEdit.Normal)
        else:
            self.password.setEchoMode(QLineEdit.Password)
