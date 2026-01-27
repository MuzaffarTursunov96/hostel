from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QScrollArea, QFrame, QPushButton, 
    QWidget, QLineEdit,
    QMessageBox, QDateEdit,QComboBox
)
from PySide6.QtCore import Qt,QDate
from PySide6.QtGui import QCursor

from i18n import t
from .api_client import api_get,api_post


class FutureBookingsDialog(QDialog):
    def __init__(self, parent, app, branch_id, bed_id):
        super().__init__(parent)

        self.app = app
        self.branch_id = branch_id
        self.bed_id = bed_id

        # Modal behavior (replacement for grab_set)
        self.setWindowModality(Qt.ApplicationModal)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.setWindowTitle(t("future_bookings"))
        self.resize(720, 420)

        main = QVBoxLayout(self)
        main.setSpacing(12)

        # ===== TITLE =====
        title = QLabel(t("future_bookings"))
        title.setStyleSheet("font-size:20px;font-weight:600;")
        main.addWidget(title)

        # ===== TABLE CARD =====
        card = QFrame()
        card.setObjectName("TableCard")
        card.setStyleSheet("""
            QFrame#TableCard {
                background: white;
                border-radius: 12px;
                padding: 8px;
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(6)

        # ===== TABLE HEADER =====
        header = QFrame()
        header.setStyleSheet("""
            background: #f3f4f6;
            border-radius: 8px;
        """)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10, 6, 10, 6)

        headers = [
            (t("checkin_date"), 140),
            (t("checkout_date"), 140),
            (t("customer"), 200),
            (t("action"), 200),
        ]


        for text, w in headers:
            lbl = QLabel(text)
            lbl.setFixedWidth(w)
            lbl.setStyleSheet("font-weight:600;color:#374151;")
            hl.addWidget(lbl)

        hl.addStretch()
        card_layout.addWidget(header)

        # ===== SCROLL BODY =====
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setSpacing(4)
        body_layout.setContentsMargins(0, 0, 0, 0)

        rows = api_get(
            self.app,
            "/dashboard/beds/future-bookings",
            {
                "branch_id": self.branch_id,
                "bed_id": self.bed_id
            }
        )

        if not rows:
            empty = QLabel(t("no_future_bookings"))
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color:#6b7280;padding:20px;")
            body_layout.addWidget(empty)
        else:
            for i, r in enumerate(rows):
                row = QFrame()
                row.setObjectName("ListRow")

                rl = QHBoxLayout(row)
                rl.setContentsMargins(10, 6, 10, 6)

                # DATA CELLS
                cells = [
                    (r["checkin_date"], 140),
                    (r["checkout_date"], 140),
                    (r["customer_name"], 200),
                ]

                for v, w in cells:
                    lbl = QLabel(str(v))
                    lbl.setFixedWidth(w)
                    rl.addWidget(lbl)

                # ===== ACTIONS =====
                actions = QHBoxLayout()

                btn_edit = QPushButton(t("edit"))
                btn_edit.clicked.connect(
                    lambda _, booking=r: self.edit_booking(booking)
                )
                btn_edit.setCursor(QCursor(Qt.PointingHandCursor))
                # print(r.keys())



                btn_cancel = QPushButton(t("cancel"))
                btn_cancel.clicked.connect(
                    lambda _, bid=r["id"]: self.cancel_booking(bid)
                )
                btn_cancel.setCursor(QCursor(Qt.PointingHandCursor))

                actions.addWidget(btn_edit)
                actions.addWidget(btn_cancel)

                rl.addLayout(actions)
                rl.addStretch()

                body_layout.addWidget(row)


        scroll.setWidget(body)
        card_layout.addWidget(scroll)

        main.addWidget(card)
    def edit_booking(self, booking):
        EditBookingFutureDialog(
            self,
            self.app,
            booking,
            self.branch_id,
            self.refresh_after_action
        )

    def cancel_booking(self, booking_id):
        from PySide6.QtWidgets import QMessageBox

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
        self.refresh_after_action()

    def refresh_after_action(self):
        self.close()
        self.parent().refresh()   # dashboard refresh


class EditBookingFutureDialog(QDialog):
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
        self.checkin.dateChanged.connect(self.load_beds)
        self.checkout.dateChanged.connect(self.load_beds)
        # self.room_box.currentIndexChanged.connect(self.recalc_total)
        # self.bed_box.currentIndexChanged.connect(self.recalc_total)

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
            "/booking/update-future-booking",
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
