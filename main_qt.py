import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QStackedWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
import os

from views.login import LoginPage
from views.sidebar import Sidebar
from views.settings import SettingsPage
from views.rooms import RoomsPage
from views.booking import BookingPage
from views.payments import PaymentsPage
from views.dashboard import DashboardPage
from views.debts import DebtsPage
from views.ws_client import WSClient
from views.customers import CustomersPage
from views.booking_history import BookingHistoryPage
from views.root_admin_panel import RootAdminPanel

from dotenv import load_dotenv
load_dotenv()
ROOT_TELEGRAM_ID = int(os.getenv("ROOT_TELEGRAM_ID"))

API_URL = os.getenv("API_BASE_URL")




from i18n import t, set_lang
from utils.config import load_config, save_config


def resource_path(relative_path: str) -> str:
    """
    Resolve resource path for dev and PyInstaller
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class App(QMainWindow):
    def __init__(self):
        super().__init__()

        # ===== CONFIG =====
        config = load_config()
        set_lang(config.get("language", "uz"))
        self.user_id = None
        self.is_admin = False

        self.access_token = None
        self.current_branch_id = config.get("branch_id", 1)

        self.setWindowTitle(t("hostel_manager"))
        self.resize(1400, 900)

        # ===== CENTRAL =====
        self.central = QWidget()
        self.setCentralWidget(self.central)

        self.layout = QHBoxLayout(self.central)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # ===== STACK (replaces pack/pack_forget) =====
        self.stack = QStackedWidget()
        self.layout.addWidget(self.stack)

        self.sidebar = None
        self.pages = {}
        self.current_page = None

        # 🔐 start with login
        self.create_login()


    def open_root_admin(self):
        if not hasattr(self, "root_admin_panel"):
            self.root_admin_panel = RootAdminPanel(self)

        self.root_admin_panel.show()
        self.root_admin_panel.raise_()
        self.root_admin_panel.activateWindow()


    # ================= LOGIN =================
    def create_login(self):
        self.clear_stack()

        login = LoginPage(
            app=self,                # 🔥 replaces self.master
            on_success=self.after_login
        )
        self.stack.addWidget(login)
        self.stack.setCurrentWidget(login)

    def after_login(self):
        # 🔥 SYNC BRANCH FROM LOGIN (VERY IMPORTANT)
        self.current_branch_id = self.branch_id   # ← branch_id from login response

        # persist for next app start (optional)
        config = load_config()
        config["branch_id"] = self.current_branch_id
        save_config(config)

        self.current_user = {
            "user_id": self.user_id,
            "is_admin": self.is_admin,
            "telegram_id": self.telegram_id,
            "is_root": self.is_admin and self.telegram_id == ROOT_TELEGRAM_ID
        }

        self.build_main_layout()
        self.show_page("dashboard")
        self.start_ws()


        


    # ================= MAIN LAYOUT =================
    def build_main_layout(self):
        self.clear_stack()

        # Sidebar (LEFT)
        self.sidebar = Sidebar(
            on_nav=self.handle_nav,
            current_user=self.current_user,
            on_branch_change=self.change_branch
        )

        self.layout.insertWidget(0, self.sidebar)

        # Pages (RIGHT)
        self.pages = {
            "dashboard": DashboardPage(self, self.current_branch_id),
            "rooms": RoomsPage(self, self.current_branch_id),
            "bookings": BookingPage(self, self.current_branch_id),
            "booking_history": BookingHistoryPage(self, self.current_branch_id),
            "customers": CustomersPage(self, self.current_branch_id),
            "payments": PaymentsPage(self, self.current_branch_id),
            "debts": DebtsPage(self, self.current_branch_id),
            "settings": SettingsPage(self)
        }

        for page in self.pages.values():
            self.stack.addWidget(page)

    # ================= NAVIGATION =================
    def handle_nav(self, page):
        if page == "logout":
            QApplication.quit()
            return

        if page == "root_admin":
            self.open_root_admin()
            return

        self.show_page(page)


    def show_page(self, name):
        page = self.pages[name]
        self.stack.setCurrentWidget(page)
        self.current_page = page

        if hasattr(page, "refresh"):
            page.refresh()

    # ================= BRANCH =================
    def change_branch(self, branch_id):
        self.current_branch_id = branch_id

        config = load_config()
        config["branch_id"] = branch_id
        save_config(config)

        # update pages safely
        for page in self.pages.values():
            if hasattr(page, "set_branch"):
                page.set_branch(branch_id)
            
            elif hasattr(page, "refresh"):
                page.refresh()

        # 🔐 SAFETY CHECK
        if "dashboard" in self.pages:
            self.show_page("dashboard")


    # ================= WS =================
    def start_ws(self):
        self.ws_client = WSClient(
            url="wss://hmsuz.com/ws",
            on_event=self.on_ws_event
        )
        self.ws_client.start()

    def on_ws_event(self, data):
        branch_id = data.get("branch_id")
        if branch_id != self.current_branch_id:
            return

        event_type = data.get("type")
        print(event_type,' >>> ',data)

        # ---------- ROOMS / BEDS ----------
        if event_type == "beds_changed":
            page = self.pages.get("rooms")
            if page and page.current_room_id == data.get("room_id"):
                page.load_beds()
            return

        if event_type == "rooms_changed":
            page = self.pages.get("rooms")
            if page:
                page.load_rooms()
            return

        # ---------- BOOKINGS ----------
        if event_type == "booking_changed":
            page = self.pages.get("bookings")
            if page:
                page.refresh()

            # dashboard numbers also depend on bookings
            dashboard = self.pages.get("dashboard")
            if dashboard:
                dashboard.refresh()
            return

        # ---------- PAYMENTS ----------
        if event_type == "payments_changed":
            page = self.pages.get("payments")
            if page:
                page.refresh()

            dashboard = self.pages.get("dashboard")
            if dashboard:
                dashboard.refresh()
            return

        # ---------- FALLBACK (safe) ----------
        if self.current_page and hasattr(self.current_page, "refresh"):
            self.current_page.refresh()


    # ================= UTILS =================
    def clear_stack(self):
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()

    def closeEvent(self, event):
        if hasattr(self, "ws_client"):
            self.ws_client.stop()
        event.accept()


    def reload_ui(self):
        """
        Rebuild UI after language change (Qt-safe)
        """
        # remove sidebar
        if self.sidebar:
            self.layout.removeWidget(self.sidebar)
            self.sidebar.deleteLater()
            self.sidebar = None

        # remove all pages
        self.clear_stack()
        self.pages.clear()
        self.current_page = None

        # rebuild everything
        self.build_main_layout()

        # show dashboard again
        self.show_page("dashboard")


    





def load_style(app):
    try:
        with open(resource_path("style.qss"), "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    except Exception as e:
        print("Style load failed:", e)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # ===== SET APPLICATION ICON =====
    icon_path = resource_path("assets/app1.ico")
    app.setWindowIcon(QIcon(icon_path))

    load_style(app)

    window = App()
    window.showMaximized()
    sys.exit(app.exec())

