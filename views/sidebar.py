from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QPushButton,
    QLabel, QSizePolicy
)
from PySide6.QtCore import Qt,QSize
from PySide6.QtGui import QIcon,QPixmap,QCursor
import os

from .brand import BrandWidget
from .utils import resource_path

from i18n import t


class NavButton(QPushButton):
    def __init__(self, text, icon_path, page_key, callback):
        super().__init__(text)

        self.page_key = page_key
        self.clicked.connect(lambda: callback(page_key))

        self.setIcon(QIcon(icon_path))
        self.setIconSize(QSize(20, 20))
        self.setCursor(Qt.PointingHandCursor)

        self.setProperty("nav", "true")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(44)


class Sidebar(QFrame):
    def __init__(self, on_nav, current_user, on_branch_change=None):
        super().__init__()
        self.current_user = current_user

        self.on_nav = on_nav
        self.on_branch_change = on_branch_change

        self.buttons = {}

        self.setObjectName("Sidebar")
        self.setFixedWidth(240)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 14)

        layout.setSpacing(8)

        brand = BrandWidget()
        layout.addWidget(brand)
        layout.setAlignment(brand, Qt.AlignHCenter)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #E5E7EB;")
        layout.addWidget(line)







        # ===== Menu =====
        self.add_btn(layout, t("dashboard"), "dashboard", resource_path("assets/icons/dashboard.png"))
        self.add_btn(layout, t("rooms"), "rooms", resource_path("assets/icons/rooms.png"))
        self.add_btn(layout, t("bookings"), "bookings", resource_path("assets/icons/booking.png"))
        self.add_btn(layout, t("booking_history"), "booking_history", resource_path("assets/icons/history.png"))
        self.add_btn(layout, t("customers"), "customers", resource_path("assets/icons/group.png"))
        self.add_btn(layout, t("payments"), "payments", resource_path("assets/icons/payment.png"))
        self.add_btn(layout, t("debts"), "debts", resource_path("assets/icons/money.png"))
        self.add_btn(layout, t("settings"), "settings", resource_path("assets/icons/settings.png"))

                # ===== Root Admin (ONLY FOR ROOT) =====
        if (
            self.current_user.get("is_admin")
            and self.current_user.get("is_root")
        ):
            self.add_btn(
                layout,
                "Root Admin",
                "root_admin",
                "assets/icons/root.png"
            )



        layout.addStretch()

        # ===== Logout =====
        logout = QPushButton("  " + t("logout"))
        logout.setIcon(QIcon(resource_path("assets/icons/logout.png")))
        
        logout.setProperty("danger", "true")
        logout.setFixedHeight(42)
        logout.clicked.connect(lambda: self.on_nav("logout"))
        layout.addWidget(logout)
        logout.setCursor(QCursor(Qt.PointingHandCursor))

        self.set_active("dashboard")

    # ==========================
    def add_btn(self, layout, label, key, icon):
        btn = NavButton(label, icon, key, self.handle_click)
        layout.addWidget(btn)
        self.buttons[key] = btn

    def handle_click(self, key):
        self.set_active(key)
        self.on_nav(key)

    def set_active(self, key):
        for k, btn in self.buttons.items():
            btn.setProperty("active", k == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
