from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QPushButton, QGridLayout,
    QDateEdit, QDialog
)
from PySide6.QtCore import Qt, QDate, QTimer, QSize
from PySide6.QtGui import QIcon,QPixmap

from datetime import datetime

from .api_client import api_get
from i18n import t
from layouts.flow_layout import FlowLayout

class CountdownBox(QFrame):
    def __init__(self, end_time=None, static=False):
        super().__init__()
        self.end_time = end_time
        self.static = static

        self.setFixedHeight(70)

        layout = QVBoxLayout(self)
        self.label = QLabel("00:00:00")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        if static:
            self.label.setText("—")
        else:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_time)
            self.timer.start(1000)
            self.update_time()

    def update_time(self):
        delta = self.end_time - datetime.now()
        if delta.total_seconds() <= 0:
            self.label.setText("00:00:00")
            self.timer.stop()
            return

        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        seconds = delta.seconds % 60
        self.label.setText(f"{hours:02}:{minutes:02}:{seconds:02}")


class CalendarBedCell(QFrame):
    def __init__(self, bed, on_click):
        super().__init__()

        self.bed = bed
        self.on_click = on_click
        self.checkout = (
            datetime.fromisoformat(bed["checkout_date"])
            if bed.get("is_busy")
            else None
        )

        self.setCursor(Qt.PointingHandCursor)
        self.mousePressEvent = lambda e: self.on_click(bed.get("bed_id"))

        self.setMinimumSize(110, 130)
        self.setMaximumSize(130, 150)
        self.setObjectName("CalendarBed")
        self.setAttribute(Qt.WA_StyledBackground, True)

        main = QVBoxLayout(self)
        main.setSpacing(0)
        main.setContentsMargins(0, 0, 0, 0)

        # ===== HEADER =====
        # ===== HEADER =====
        self.header = QFrame()
        self.header.setObjectName("BedHeader")
        self.header.setFixedHeight(42)
        self.header.setAttribute(Qt.WA_StyledBackground, True)

        header_layout = QVBoxLayout(self.header)
        header_layout.setContentsMargins(6, 4, 6, 4)
        header_layout.setSpacing(2)

        # --- TOP ROW: title + icon ---
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        title = QLabel(f"{t('bed')} #{bed['bed_number']}")
        title.setObjectName("BedTitle")
        title.setStyleSheet("font-size:9px;font-weight:600;")


        top_row.addWidget(title)
        top_row.addStretch()

        # future icon (INLINE, NOT NEW LINE)
        if bed.get("has_future"):
            icon = QLabel()
            pix = QPixmap("assets/icons/calendar.png")
            icon.setPixmap(
                pix.scaled(14, 14, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            icon.setCursor(Qt.PointingHandCursor)
            icon.setToolTip(t("future_bookings"))

            icon.mousePressEvent = (
                lambda e, bid=bed["bed_id"]:
                (e.accept(), self.on_click(bid))
            )

            top_row.addWidget(icon)

        header_layout.addLayout(top_row)

        # --- CHECKOUT (NEW LINE ✅) ---
        self.checkout_lbl = QLabel()
        self.checkout_lbl.setObjectName("BedCheckout")
        self.checkout_lbl.setStyleSheet("font-size:9px;color:#6b7280;")

        header_layout.addWidget(self.checkout_lbl)

        # --- STATUS LINE (BOTTOM) ---
        status_bar = QFrame()
        status_bar.setFixedHeight(1)
        status_bar.setObjectName(
            "BedStatusBusy" if bed["is_busy"] else "BedStatusFree"
        )
        header_layout.addWidget(status_bar)
        

        # ===== BODY (THIS WAS INVISIBLE) =====
        body = QFrame()
        body.setObjectName("BedBody")
        body.setAttribute(Qt.WA_StyledBackground, True)

        grid = QGridLayout(body)
        grid.setContentsMargins(3, 3, 3, 3)
        grid.setSpacing(3)

        self.cells = {}

        for r, c, key, label in [
            (0, 0, "days", t("days")),
            (0, 1, "hours", t("hours")),
            (1, 0, "minutes", t("minutes")),
            (1, 1, "seconds", t("seconds")),
        ]:
            num = QLabel("00")
            num.setAlignment(Qt.AlignCenter)
            num.setStyleSheet("font-size:12px;font-weight:700;")

            txt = QLabel(label)
            txt.setAlignment(Qt.AlignCenter)
            txt.setStyleSheet("font-size:9px;color:#9ca3af;")

            v = QVBoxLayout()
            v.setSpacing(1)
            v.addWidget(num)
            v.addWidget(txt)

            frame = QFrame()
            frame.setLayout(v)
            grid.addWidget(frame, r, c)

            self.cells[key] = num

        main.addWidget(body, 1)  # 🔥 THIS FIXES VISIBILITY
        
        main.addWidget(self.header)


        # ===== TIMER =====
        if self.checkout:
            self.checkout_lbl.setText(
                f"{t('checkout')}: {self.checkout:%d %b %Y}"
            )
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_time)
            self.timer.start(1000)
            self.update_time()
        else:
            self.checkout_lbl.setText(t("free_now"))
            self.update_free()

    def update_time(self):
        if not self.checkout:
            return

        delta = self.checkout - datetime.now()
        if delta.total_seconds() <= 0:
            self.timer.stop()
            for lbl in self.cells.values():
                lbl.setText("00")
            return

        self.cells["days"].setText(f"{delta.days:02}")
        self.cells["hours"].setText(f"{(delta.seconds // 3600) % 24:02}")
        self.cells["minutes"].setText(f"{(delta.seconds // 60) % 60:02}")
        self.cells["seconds"].setText(f"{delta.seconds % 60:02}")

    def update_free(self):
        for lbl in self.cells.values():
            lbl.setText("00")
        self.checkout_lbl.setText("")


class DashboardPage(QWidget):
    def __init__(self, app, branch_id):
        super().__init__()
        self.app = app
        self.branch_id = branch_id

        main = QVBoxLayout(self)

        # ===== Header =====
        # ===== Header Bar =====
        header_bar = QHBoxLayout()
        header_bar.setSpacing(12)

        # Title (LEFT)
        title = QLabel(t("room_availability_now"))
        title.setStyleSheet("font-size:16px;font-weight:600;")
        header_bar.addWidget(title)

        header_bar.addStretch()

        active_btn = QPushButton(t("active_bookings"))
        active_btn.setFixedHeight(32)
        active_btn.setProperty("primary", "true")

        active_btn.setIcon(QIcon("assets/icons/active_booking.png"))  # <-- your icon path
        active_btn.setIconSize(QSize(18, 18))

        active_btn.clicked.connect(self.open_active_bookings)

        header_bar.addWidget(active_btn)


        # ===== Filter Card (RIGHT) =====
        filter_card = QFrame()
        filter_card.setObjectName("FilterBar")

        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(4, 2, 4, 2)
        filter_layout.setSpacing(3)

        self.from_date = QDateEdit(QDate.currentDate())
        self.from_date.setCalendarPopup(True)

        self.to_date = QDateEdit(QDate.currentDate())
        self.to_date.setCalendarPopup(True)

        self.to_date.setCalendarPopup(True)

        filter_btn = QPushButton(t("search"))
        filter_btn.setIcon(QIcon("assets/icons/search.png"))
        filter_btn.clicked.connect(self.apply_date_filter)

        reset_btn = QPushButton(t("reset"))
        reset_btn.setIcon(QIcon("assets/icons/refresh.png"))  # optional icon
        reset_btn.clicked.connect(self.reset_filter)

        filter_layout.addWidget(self.from_date)
        filter_layout.addWidget(self.to_date)
        filter_layout.addWidget(filter_btn)
        filter_layout.addWidget(reset_btn)


        header_bar.addWidget(filter_card)

        main.addLayout(header_bar)


        # ===== Scroll =====
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setSpacing(8)

        scroll.setWidget(self.container)
        main.addWidget(scroll)

        self.refresh()

    def set_branch(self, branch_id):
        self.branch_id = branch_id
        self.refresh()
    
    def apply_date_filter(self):
        self._filter_checkin = self._date_to_str(self.from_date.date())
        self._filter_checkout = self._date_to_str(self.to_date.date())
        self.refresh()

    def reset_filter(self):
    # clear internal filter state
        self._filter_checkin = None
        self._filter_checkout = None

        # reset UI dates (UX)
        today = QDate.currentDate()
        self.from_date.setDate(today)
        self.to_date.setDate(today)

        # reload without filters
        self.refresh()



    def refresh(self):
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.deleteLater()

        params = {"branch_id": self.branch_id}

        if hasattr(self, "_filter_checkin") and self._filter_checkin:
            params["checkin_date"] = self._filter_checkin

        if hasattr(self, "_filter_checkout") and self._filter_checkout:
            params["checkout_date"] = self._filter_checkout


        rooms = api_get(
            self.app,
            "/dashboard/rooms",
            params
        )

        now = datetime.now()
        for i, room in enumerate(rooms):
            room_card = self.create_room_card(room)
            r, c = divmod(i, 2)
            self.grid.addWidget(room_card, r, c)

    def _date_to_str(self, qdate):
        if not qdate:
            return None
        return qdate.toString("yyyy-MM-dd")


    def create_room_card(self, room):
        card = QFrame()
        card.setObjectName("RoomCard")

        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        title = QLabel(f"{t('room')} {room['room_number']}")
        title.setStyleSheet("font-size:10px;font-weight:600;")
        layout.addWidget(title)

        beds_flow = FlowLayout(spacing=4)

        for bed in room["beds"]:
            beds_flow.addWidget(
                CalendarBedCell(bed, self.open_future_modal)
            )

        layout.addLayout(beds_flow)

                # layout.addLayout(beds_grid)
        return card

    def open_active_bookings(self):
        from .active_bookings import ActiveBookingsDialog

        dlg = ActiveBookingsDialog(
            self,
            self.app,
            self.branch_id,
            0
        )
        dlg.exec()


    def open_future_modal(self, bed_id):
        from .future_bookings import FutureBookingsDialog

        dlg = FutureBookingsDialog(
            self,          # parent = dashboard
            self.app,
            self.branch_id,
            bed_id
        )
        dlg.exec()
