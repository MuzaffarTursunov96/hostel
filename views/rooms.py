from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QMessageBox
)
from PySide6.QtCore import Qt,QSize
from PySide6.QtGui import QCursor,QIcon

from i18n import t
from .api_client import api_get, api_post, api_delete
from .utils import resource_path





class RoomsPage(QWidget):
    def __init__(self, app, branch_id):
        super().__init__()

        

        self.app = app
        self.branch_id = branch_id

        self.current_room = None
        self.current_room_id = None
        self.selected_bed = None

        self.room_buttons = {}
        self.bed_buttons = {}

        root = QHBoxLayout(self)
        root.setSpacing(16)

        # ================= LEFT: ROOMS =================
        rooms_panel = QFrame()
        rooms_panel.setFixedWidth(310)
        rooms_layout = QVBoxLayout(rooms_panel)
        rooms_layout.setSpacing(8)

        rooms_layout.addWidget(QLabel(t("rooms")))

        self.rooms_scroll = QScrollArea()
        self.rooms_scroll.setWidgetResizable(True)

        self.rooms_container = QWidget()
        self.rooms_list = QVBoxLayout(self.rooms_container)
        self.rooms_list.setAlignment(Qt.AlignTop)
        self.rooms_list.setSpacing(6)

        self.rooms_scroll.setWidget(self.rooms_container)
        rooms_layout.addWidget(self.rooms_scroll, 1)

        # room actions
        # ================= ROOM ACTIONS =================
        room_actions = QHBoxLayout()

        btn_add_room = QPushButton(t("add_room"))
        btn_add_room.setIcon(QIcon(resource_path("assets/icons/room-add.png")))
        btn_add_room.setIconSize(QSize(18, 18))
        btn_add_room.clicked.connect(self.add_room)
        btn_add_room.setCursor(QCursor(Qt.PointingHandCursor))

        btn_delete_room = QPushButton(t("delete_room"))
        btn_delete_room.setIcon(QIcon(resource_path("assets/icons/room-delete.png")))
        btn_delete_room.setIconSize(QSize(18, 18))
        btn_delete_room.clicked.connect(self.delete_room)
        btn_delete_room.setCursor(QCursor(Qt.PointingHandCursor))

        room_actions.addWidget(btn_add_room)
        room_actions.addWidget(btn_delete_room)
        rooms_layout.addLayout(room_actions)



        root.addWidget(rooms_panel)

        # ================= RIGHT: BEDS =================
        beds_panel = QFrame()
        beds_layout = QVBoxLayout(beds_panel)
        beds_layout.setSpacing(8)

        self.beds_title = QLabel("")
        beds_layout.addWidget(self.beds_title)

        self.beds_scroll = QScrollArea()
        self.beds_scroll.setWidgetResizable(True)

        self.beds_container = QWidget()
        self.beds_list = QVBoxLayout(self.beds_container)
        self.beds_list.setAlignment(Qt.AlignTop)
        self.beds_list.setSpacing(6)

        self.beds_scroll.setWidget(self.beds_container)
        beds_layout.addWidget(self.beds_scroll, 1)

        # bed actions
        # ================= BED ACTIONS =================
        bed_actions = QHBoxLayout()

        btn_add_bed = QPushButton(t("add_bed"))
        btn_add_bed.setIcon(QIcon(resource_path("assets/icons/bed-add.png")))
        btn_add_bed.setIconSize(QSize(18, 18))
        btn_add_bed.clicked.connect(self.add_bed)
        btn_add_bed.setCursor(QCursor(Qt.PointingHandCursor))

        btn_delete_bed = QPushButton(t("delete_bed"))
        btn_delete_bed.setIcon(QIcon(resource_path("assets/icons/bed-delete.png")))
        btn_delete_bed.setIconSize(QSize(18, 18))
        btn_delete_bed.clicked.connect(self.delete_bed)
        btn_delete_bed.setCursor(QCursor(Qt.PointingHandCursor))

        bed_actions.addWidget(btn_add_bed)
        bed_actions.addWidget(btn_delete_bed)
        bed_actions.addStretch()

        beds_layout.addLayout(bed_actions)
        root.addWidget(beds_panel, 1)

        self.load_rooms()

        
    def set_branch(self, branch_id):
        self.branch_id = branch_id
        self.refresh()

    # ================= ROOMS =================
    def load_rooms(self):
        self.room_buttons.clear()
        while self.rooms_list.count():
            self.rooms_list.takeAt(0).widget().deleteLater()

        rooms = api_get(self.app, "/rooms/", {"branch_id": self.branch_id})

        for room in rooms:
            btn = QPushButton(f"{t('room')} {room['room_number']}")
            btn.setFixedHeight(30)
            btn.setProperty("room", True)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.clicked.connect(lambda _, r=room: self.select_room(r))
            self.rooms_list.addWidget(btn)
            self.room_buttons[room["id"]] = btn

        if rooms:
            self.select_room(rooms[0])

    def select_room(self, room):
        self.current_room = room
        self.current_room_id = room["id"]
        self.selected_bed = None

        for rid, btn in self.room_buttons.items():
            btn.setProperty("active", rid == room["id"])
            btn.style().polish(btn)

        self.beds_title.setText(
            f"{t('room')} {room['room_number']} — {t('beds')}"
        )
        self.load_beds()

    def add_room(self):
        next_number = self._next_room_number()

        api_post(
            self.app,
            "/rooms/",
            {
                "branch_id": self.branch_id,
                "number": next_number
            }
        )

        self.load_rooms()
        self.refresh_dashboard()
    
    def _next_room_number(self):
        """
        Generates next room number based on existing rooms.
        SAME LOGIC as old Tkinter app (auto increment).
        """
        rooms = api_get(
            self.app,
            "/rooms/",
            {"branch_id": self.branch_id}
        )

        numbers = []
        for r in rooms:
            try:
                numbers.append(int(r["room_number"]))
            except (ValueError, TypeError, KeyError):
                pass

        return str(max(numbers) + 1) if numbers else "1"


    def delete_room(self):
        if not self.current_room_id:
            return

        # 🔒 check if room has any booked bed
        has_bookings = api_get(
            self.app,
            f"/rooms/{self.current_room_id}/has-bookings",
            {"branch_id": self.branch_id}
        )["has_booking"]

        if has_bookings:
            QMessageBox.warning(
                self,
                t("error"),
                t("room_has_booked_beds")
            )
            return

        if QMessageBox.question(
            self, t("confirm"), t("delete_room_and_beds")
        ) != QMessageBox.Yes:
            return

        api_delete(
                self.app,
                f"/rooms/{self.current_room_id}",
                {"branch_id": self.branch_id}
            )

        self.current_room_id = None
        self.load_rooms()
        self.refresh_dashboard()


    # ================= BEDS =================
    def load_beds(self):
        self.bed_buttons.clear()
        while self.beds_list.count():
            self.beds_list.takeAt(0).widget().deleteLater()

        # 1️⃣ get all beds
        beds = api_get(
            self.app,
            "/beds/",
            {
                "branch_id": self.branch_id,
                "room_id": self.current_room_id
            }
        )

        # 2️⃣ get busy beds ONCE
        resp = api_get(
            self.app,
            "/beds/busy-now",
            {
                "branch_id": self.branch_id,
                "room_id": self.current_room_id
            }
        )

        busy_beds = set(resp.get("busy_beds", []))

        # 3️⃣ render UI
        for bed in beds:
            busy = bed["id"] in busy_beds

            btn = QPushButton(
                f"{t('bed')} {bed['bed_number']} — "
                f"{t('busy') if busy else t('free')}"
            )
            btn.setFixedHeight(32)
            btn.setProperty("busy", busy)
            btn.clicked.connect(
                lambda _, bid=bed["id"]: self.select_bed(bid)
            )
            btn.setCursor(QCursor(Qt.PointingHandCursor))

            self.beds_list.addWidget(btn)
            self.bed_buttons[bed["id"]] = btn


    def select_bed(self, bed_id):
        self.selected_bed = bed_id
        for bid, btn in self.bed_buttons.items():
            btn.setProperty("selected", bid == bed_id)
            btn.style().polish(btn)

    def add_bed(self):
        if not self.current_room_id:
            return

        api_post(
            self.app,
            "/beds/",
            {"branch_id": self.branch_id, "room_id": self.current_room_id}
        )
        self.load_beds()
        self.refresh_dashboard()

    def delete_bed(self):
        if not self.selected_bed:
            return

        # 🔒 check if bed has any booking (today or future)
        has_booking = api_get(
            self.app,
            f"/beds/{self.selected_bed}/has-bookings",
            {"branch_id": self.branch_id}
        )["has_booking"]

        if has_booking:
            QMessageBox.warning(
                self,
                t("error"),
                t("bed_has_bookings_cannot_delete")
            )
            return

        status_del = api_delete(self.app, f"/beds/{self.selected_bed}")

        if status_del['status'] == 500:
            QMessageBox.warning(
                self,
                t("error"),
                t("cannot_delete_bed_reason")
            )
        else:
            QMessageBox.information(
                self,
                t("success"),
                t("operation_completed_successfully")
            )
        self.selected_bed = None
        self.load_beds()
        self.refresh_dashboard()


    # ================= STATUS =================
    def toggle_status(self):
        if not self.selected_bed:
            return

        booking = self.app.pages["bookings"]
        self.app.show_page("bookings")
        booking.prefill_from_rooms(
            self.current_room_id,
            self.selected_bed
        )

    # ================= HELPERS =================
    def refresh_dashboard(self):
        dashboard = self.app.pages.get("dashboard")
        if dashboard:
            dashboard.refresh()

    def refresh(self):
        self.load_rooms()
        if self.current_room_id:
            self.load_beds()

