from PySide6.QtWidgets import (
    QWidget,  # ✅ ADD THIS
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QScrollArea, QLineEdit,
    QMessageBox, QDateEdit,QComboBox
)
from PySide6.QtGui import QCursor
from PySide6.QtCore import Qt, QTimer, QDate
from datetime import datetime, date


from i18n import t
from .api_client import api_get, api_post

class ActiveBookingsDialog(QDialog):
    def __init__(self, parent, app, branch_id, bed_id):
        super().__init__(parent)
        self.dashboard = parent
        self.app = app
        self.branch_id = branch_id
        self.bed_id = bed_id



        self.setWindowTitle(t("active_bookings"))
        self.resize(1200, 500)
        self.setModal(True)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.apply_customer_filter)

        main = QVBoxLayout(self)

        # ===== TITLE =====
        title = QLabel(t("active_bookings_beds"))
        title.setObjectName("PageTitle")
        main.addWidget(title)

        # ===== TABLE =====
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.container = QWidget()
        self.table = QVBoxLayout(self.container)
        self.table.setSpacing(4)

        self.scroll.setWidget(self.container)
        main.addWidget(self.scroll)

        self.draw_header()
        self.load()

    def draw_header(self):
        header = QFrame()
        header.setObjectName("ListCard")
        hl = QVBoxLayout(header)

        titles = [
            "customer", "passport_id", "room", "bed",
            "checkin_date", "checkout_date", "total_amount", "action"
        ]
        widths = [180, 100, 70, 70, 120, 120, 100, 200]

        row_titles = QHBoxLayout()
        for text, w in zip(titles, widths):
            lbl = QLabel(t(text))
            lbl.setFixedWidth(w)
            lbl.setStyleSheet("font-weight:600")
            row_titles.addWidget(lbl)
        hl.addLayout(row_titles)

        # ---- search row ----
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(t("search_customer"))
        self.search_input.setFixedWidth(widths[0])
        self.search_input.textChanged.connect(
            lambda: self.search_timer.start(300)
        )
        search_row.addWidget(self.search_input)
        search_row.addStretch()

        hl.addLayout(search_row)
        self.table.addWidget(header)

    def load(self):
        while self.table.count() > 1:
            w = self.table.takeAt(1).widget()
            if w:
                w.deleteLater()

        rows = api_get(
            self.app,
            "/active-bookings/",
            {"branch_id": self.branch_id}
        )

        if not rows:
            self.table.addWidget(QLabel(t("no_active_bookings")))
            return

        for r in rows:
            self.add_row(r)

    def add_row(self, r):
        row = QFrame()
        row.setObjectName("ListRow")
        row.customer_name = r["customer_name"]
        row.passport_id = r["passport_id"]

        layout = QHBoxLayout(row)
        layout.setSpacing(6)

        values = [
            r["customer_name"],
            r["passport_id"],
            str(r["room_number"]),
            str(r["bed_number"]),
            self.format_date(r["checkin_date"]),
            self.format_date(r["checkout_date"]),
            f"{r['total_amount']:.2f}"
        ]
        widths = [180, 100, 70, 70, 120, 120, 100]

        for v, w in zip(values, widths):
            lbl = QLabel(v)
            lbl.setFixedWidth(w)
            layout.addWidget(lbl)

        actions = QHBoxLayout()

        btn_edit = QPushButton(t("edit"))
        btn_edit.clicked.connect(lambda: self.edit_booking(r))
        btn_edit.setCursor(QCursor(Qt.PointingHandCursor))

        btn_cancel = QPushButton(t("cancel"))
        btn_cancel.clicked.connect(
            lambda: self.cancel_booking_action(r["id"])
        )
        btn_cancel.setCursor(QCursor(Qt.PointingHandCursor))

        actions.addWidget(btn_edit)
        actions.addWidget(btn_cancel)
        layout.addLayout(actions)

        self.table.addWidget(row)

    def cancel_booking_action(self, booking_id):
        if QMessageBox.question(
            self,
            t("cancel_booking"),
            t("are_you_sure_cancel_booking")
        ) != QMessageBox.Yes:
            return

        api_post(
            self.app,
            "/active-bookings/cancel",
            {
                "booking_id": booking_id,
                "branch_id": self.branch_id
            }
        )

        QMessageBox.information(self, t("canceled"), t("canceled_text"))
        self.refresh()
        self.dashboard.refresh()

    def edit_booking(self, booking):
        self.edit_dialog = EditBookingDialog(
            self,
            self.app,
            booking,
            self.branch_id,
            self.on_edit_done
        )
        self.edit_dialog.show()


    def on_edit_done(self):
        self.refresh()
        self.dashboard.refresh()

    def apply_customer_filter(self):
        query = self.search_input.text().strip().lower()

        for i in range(1, self.table.count()):
            row = self.table.itemAt(i).widget()
            if not hasattr(row, "customer_name"):
                continue

            name = (row.customer_name or "").lower()
            passport = (row.passport_id or "").lower()

            row.setVisible(
                not query or query in name or query in passport
            )

    def format_date(self, d):
        if isinstance(d, str):
            d = datetime.fromisoformat(d)
        return d.strftime("%d %b %Y")

    def refresh(self):
        self.load()

class EditBookingDialog(QDialog):
    def __init__(self, parent, app, booking,branch_id, on_done):
        super().__init__(parent)

        self.app = app
        self.booking = booking
        self.on_done = on_done
        self.branch_id = branch_id

        self.setWindowTitle(t("edit_booking"))
        self.resize(400, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)

        

        self.checkin = QDateEdit()
        self.checkin.setCalendarPopup(True)
        self.checkin.setDate(
            QDate.fromString(booking["checkin_date"], "yyyy-MM-dd")
        )
        self.checkout = QDateEdit()
        self.checkout.setCalendarPopup(True)
        self.checkout.setDate(
            QDate.fromString(booking["checkout_date"], "yyyy-MM-dd")
        )

        self.room_box = QComboBox()
        

        layout.addWidget(QLabel(t("room")))
        layout.addWidget(self.room_box)

        self.bed_box = QComboBox()
        layout.addWidget(QLabel(t("bed")))
        layout.addWidget(self.bed_box)



        self.amount = QLineEdit(str(booking["total_amount"]))

        save_btn = QPushButton(t("save"))
        save_btn.clicked.connect(self.save)
        save_btn.setCursor(QCursor(Qt.PointingHandCursor))

        layout.addWidget(self.checkin)
        layout.addWidget(self.checkout)
        layout.addWidget(self.amount)
        layout.addWidget(save_btn)
        self.checkout.dateChanged.connect(self.load_beds)
        self.room_box.currentIndexChanged.connect(self.recalc_total)
        self.bed_box.currentIndexChanged.connect(self.recalc_total)

        self.load_rooms()

        self.show()

    def load_rooms(self):
        rooms = api_get(
            self.app,
            "/rooms/",
            {"branch_id": self.branch_id}
        )

        self.room_box.clear()

        for r in rooms:
            self.room_box.addItem(
                str(r["room_number"]),  # display
                r["id"]                 # data = room_id
            )

        # 🔥 IMPORTANT: connect ONCE
        self.room_box.currentIndexChanged.connect(self.load_beds)

        # ✅ select current room by room_id (DATA, not TEXT)
        for i in range(self.room_box.count()):
            if self.room_box.itemData(i) == self.booking["room_id"]:
                self.room_box.setCurrentIndex(i)
                break

        self.load_beds()



    
    def load_beds(self):
        room_id = self.room_box.currentData()
        if not room_id:
            return

        beds = api_get(
            self.app,
            "/beds/",
            {
                "branch_id": self.branch_id,
                "room_id": room_id
            }
        )

        busy = api_get(
            self.app,
            "/beds/busy",
            {
                "branch_id": self.branch_id,
                "room_id": room_id,
                "checkin": self.booking["checkin_date"],
                "checkout": self.checkout.date().toString("yyyy-MM-dd"),
                "exclude_booking_id": self.booking["id"]
            }
        )["busy_beds"]

        self.bed_box.clear()

        for b in beds:
            bed_id = b["id"]

            # ✅ show if free OR if it's the current booking bed
            if bed_id in busy and bed_id != self.booking["bed_id"]:
                continue

            self.bed_box.addItem(
                f"{t('bed')} {b['bed_number']}",
                bed_id
            )

        # ✅ SELECT CURRENT BED
        for i in range(self.bed_box.count()):
            if self.bed_box.itemData(i) == self.booking["bed_id"]:
                self.bed_box.setCurrentIndex(i)
                break


    
    def recalc_total(self):

        checkin = QDate.fromString(
            self.booking["checkin_date"], "yyyy-MM-dd"
        )
        checkout = self.checkout.date()

        days_old = checkin.daysTo(
            QDate.fromString(
                self.booking["checkout_date"], "yyyy-MM-dd"
            )
        )
        if days_old <= 0:
            return

        price_per_day = self.booking["total_amount"] / days_old

        days_new = checkin.daysTo(checkout)
        if days_new <= 0:
            return

        new_total = round(days_new * price_per_day, 2)
        self.amount.setText(str(new_total))



    def save(self):
        api_post(
            self.app,
            "/active-bookings/update-admin",
            {
                "booking_id": self.booking["id"],
                "room_id": self.room_box.currentData(),
                "bed_id": self.bed_box.currentData(),
                "checkin_date": self.checkin.date().toString("yyyy-MM-dd"),
                "checkout_date": self.checkout.date().toString("yyyy-MM-dd"),
                "total_amount": float(self.amount.text())
            }
        )



        QMessageBox.information(self, t("saved"), t("booking_updated"))
        self.on_done()
        self.accept()
