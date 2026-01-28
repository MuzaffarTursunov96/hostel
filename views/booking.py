from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QScrollArea,
    QComboBox, QMessageBox, QDateEdit,QCompleter
)
from PySide6.QtCore import Qt, QDate, QSize
from PySide6.QtGui import QCursor,QIcon

from .api_client import api_get, api_post
from i18n import t


class BookingPage(QWidget):
    def __init__(self, app, branch_id):
        super().__init__()

        self.app = app
        self.branch_id = branch_id

        self.current_room_id = None
        self.selected_bed_id = None
        self.prefilled_bed_id = None

        self.build_ui()
        self.load_rooms()

    def section_title(self, text, icon_path):
        row = QHBoxLayout()

        icon = QLabel()
        icon.setPixmap(QIcon(icon_path).pixmap(18, 18))

        label = QLabel(text)
        label.setStyleSheet("font-size:15px;font-weight:600;")

        row.addWidget(icon)
        row.addWidget(label)
        row.addStretch()

        w = QWidget()
        w.setLayout(row)
        return w

    # ================= UI =================
    def build_ui(self):
        main = QVBoxLayout(self)

        title = QLabel(t("book_a_room"))
        title.setStyleSheet("font-size:26px;font-weight:600;")
        main.addWidget(title)

        # ===== SCROLL =====
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        main.addWidget(scroll)

        wrapper = QWidget()
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.addStretch()

        content = QWidget()
        content.setMaximumWidth(900)
        content.setStyleSheet("""
            QWidget {
                background:white;
                border-radius:16px;
            }
        """)

        wrapper_layout.addWidget(content)
        wrapper_layout.addStretch()
        scroll.setWidget(wrapper)

        layout = QVBoxLayout(content)
        layout.setSpacing(18)
        layout.setContentsMargins(24, 24, 24, 24)

        # ===== ROOM =====
        layout.addWidget(self.section_title(t("room"), "assets/icons/room.png"))

        self.room_dropdown = QComboBox()
        self.room_dropdown.setFixedHeight(38)
        self.room_dropdown.currentTextChanged.connect(self.room_selected)
        layout.addWidget(self.room_dropdown)

        # ===== DATES =====
        layout.addWidget(self.section_title(t("dates"), "assets/icons/google-calendar.png"))

        self.checkin = QDateEdit(QDate.currentDate())
        self.checkout = QDateEdit(QDate.currentDate().addDays(1))

        for d in (self.checkin, self.checkout):
            d.setCalendarPopup(True)
            d.setFixedHeight(38)
            d.dateChanged.connect(self.load_available_beds)

        dates = QHBoxLayout()

        left = QVBoxLayout()
        left.addWidget(QLabel(t("check_in")))
        left.addWidget(self.checkin)

        right = QVBoxLayout()
        right.addWidget(QLabel(t("check_out")))
        right.addWidget(self.checkout)

        dates.addLayout(left)
        dates.addLayout(right)
        layout.addLayout(dates)

        # ===== BEDS =====
        layout.addWidget(self.section_title(t("available_beds"), "assets/icons/bed.png"))

        beds_scroll = QScrollArea()
        beds_scroll.setWidgetResizable(True)
        beds_scroll.setFixedHeight(220)

        beds_widget = QWidget()
        self.beds_container = QVBoxLayout(beds_widget)
        self.beds_container.setSpacing(8)

        beds_scroll.setWidget(beds_widget)
        layout.addWidget(beds_scroll)

        # ===== CUSTOMER =====
        layout.addWidget(self.section_title(t("customer"), "assets/icons/account.png"))

        self.customer_box = QComboBox()
        self.customer_box.setEditable(True)
        self.customer_box.setInsertPolicy(QComboBox.NoInsert)
        self.customer_box.setFixedHeight(38)
        self.customer_box.activated.connect(self.on_customer_selected)
        layout.addWidget(self.customer_box)

        self.passport_entry = QLineEdit()
        self.passport_entry.setPlaceholderText(t("passport_id"))
        self.passport_entry.setFixedHeight(38)
        self.passport_entry.textChanged.connect(self.on_passport_changed)

        self.contact_entry = QLineEdit()
        self.contact_entry.setPlaceholderText(t("contact_info"))
        self.contact_entry.setFixedHeight(38)

        layout.addWidget(self.passport_entry)
        layout.addWidget(self.contact_entry)

        # ===== PAYMENT =====
        layout.addWidget(self.section_title(t("payment"), "assets/icons/usd.png"))

        self.total_entry = QLineEdit()
        self.total_entry.setPlaceholderText(t("total_amount"))
        self.total_entry.setFixedHeight(38)
        self.total_entry.textChanged.connect(self.update_remaining)

        self.paid_entry = QLineEdit()
        self.paid_entry.setPlaceholderText(t("paid_amount"))
        self.paid_entry.setFixedHeight(38)
        self.paid_entry.textChanged.connect(self.update_remaining)

        pay_row = QHBoxLayout()
        pay_row.addWidget(self.total_entry)
        pay_row.addWidget(self.paid_entry)
        layout.addLayout(pay_row)

        self.remaining_label = QLabel(t("remaining") + ": 0.00")
        self.remaining_label.setStyleSheet("""
            font-weight:600;
            padding:8px;
            border-radius:8px;
            background:#fef3c7;
        """)
        layout.addWidget(self.remaining_label)

        # ===== CONFIRM =====
        confirm = QPushButton(t("confirm_booking"))
        confirm.setIcon(QIcon("assets/icons/checklist2.png"))
        confirm.setIconSize(QSize(18, 18))
        confirm.setFixedHeight(48)
        confirm.setCursor(QCursor(Qt.PointingHandCursor))
        confirm.setStyleSheet("""
            QPushButton {
                background:#16a34a;
                color:white;
                font-size:16px;
                font-weight:600;
                border-radius:12px;
            }
            QPushButton:hover {
                background:#15803d;
            }
        """)
        confirm.clicked.connect(self.confirm_booking)
        layout.addWidget(confirm)




    def on_customer_selected(self, index):
        data = self.customer_box.itemData(index, Qt.UserRole)

        if not isinstance(data, dict):
            return

        self.passport_entry.setText(data["passport"])
        self.contact_entry.setText(data["contact"])



    def on_passport_changed(self, text):
        cursor_pos = self.passport_entry.cursorPosition()
        upper = text.upper()

        if text != upper:
            self.passport_entry.blockSignals(True)
            self.passport_entry.setText(upper)
            self.passport_entry.setCursorPosition(cursor_pos)
            self.passport_entry.blockSignals(False)



    # ================= LOGIC =================
    def load_rooms(self):
        rooms = api_get(self.app, "/booking/rooms", {"branch_id": self.branch_id})
        self.rooms = rooms
        self.room_dropdown.clear()

        for r in rooms:
            self.room_dropdown.addItem(
                f"{r['id']} - {t('room_number')} {r['room_number']}",
                r["id"]
            )

    def room_selected(self, text):
        if not text:
            return
        self.current_room_id = int(text.split(" - ")[0])
        self.prefilled_bed_id = None
        self.load_available_beds()

    def load_available_beds(self):
        while self.beds_container.count():
            self.beds_container.takeAt(0).widget().deleteLater()

        if not self.current_room_id:
            return

        checkin = self.checkin.date().toPython()
        checkout = self.checkout.date().toPython()

        if checkout <= checkin:
            self.beds_container.addWidget(QLabel(t("checkout_date_must_be_after_checkin")))
            return

        beds = api_get(
            self.app,
            "/booking/available-beds",
            {
                "branch_id": self.branch_id,
                "room_id": self.current_room_id,
                "checkin": checkin.isoformat(),
                "checkout": checkout.isoformat()
            }
        )

        self.selected_bed_id = None

        if not beds:
            self.beds_container.addWidget(QLabel(t("no_free_beds_available")))
            return

        for b in beds:
            btn = QPushButton(f"{t('bed')} {b['bed_number']}")
            btn.setCheckable(True)
            btn.setFixedHeight(44)

            btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid #e5e7eb;
                    border-radius: 10px;
                    background: white;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: #f3f4f6;
                }
                QPushButton:checked {
                    background: rgba(37, 99, 235, 0.5);   /* #2563eb at 50% */
                    color: white;                       /* darker blue text */
                    font-weight: 600;
                    border: 1px solid rgba(37, 99, 235, 0.8);
                }
            """)

            btn.clicked.connect(lambda _, bid=b["id"], bbtn=btn: self.select_bed(bid, bbtn))
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            self.beds_container.addWidget(btn)


    def select_bed(self, bed_id, clicked_button):
        self.selected_bed_id = bed_id

        # 🔥 uncheck all other bed buttons
        for i in range(self.beds_container.count()):
            w = self.beds_container.itemAt(i).widget()
            if isinstance(w, QPushButton) and w is not clicked_button:
                w.setChecked(False)

        clicked_button.setChecked(True)


    def update_remaining(self):
        try:
            total = float(self.total_entry.text())
            paid = float(self.paid_entry.text())
            self.remaining_label.setText(
                f"{t('remaining')}: {max(total - paid, 0):.2f}"
            )
        except:
            self.remaining_label.setText(f"{t('remaining')}: 0.00")

    def confirm_booking(self):
        if not self.selected_bed_id:
            return QMessageBox.warning(self, t("error"), t("select_a_bed"))

        name = self.customer_box.currentText().strip()

        passport = self.passport_entry.text().strip().upper()


        if not name or not passport:
            return QMessageBox.warning(self, t("error"), t("required_fields"))

        try:
            total = float(self.total_entry.text())
            paid = float(self.paid_entry.text())
        except:
            return QMessageBox.warning(self, t("error"), t("invalid_payment_values"))

        api_post(
            self.app,
            "/booking/",
            {
                "branch_id": self.branch_id,
                "name": name,
                "passport_id": passport,
                "contact": self.contact_entry.text(),
                "room_id": self.current_room_id,
                "bed_id": self.selected_bed_id,
                "total": total,
                "paid": paid,
                "checkin": self.checkin.date().toString("yyyy-MM-dd"),
                "checkout": self.checkout.date().toString("yyyy-MM-dd"),
            }
        )

        QMessageBox.information(self, t("success"), t("booking_confirmed"))
        self.reset_form()
        self.refresh()
        
        # 🔥 FORCE CUSTOMERS PAGE REFRESH
        if "customers" in self.app.pages:
            page = self.app.pages["customers"]
            if hasattr(page, "refresh"):
                page.refresh()


    def set_branch(self, branch_id):
        self.branch_id = branch_id

        # reset internal state
        self.current_room_id = None
        self.selected_bed_id = None
        self.prefilled_bed_id = None

        # reset room dropdown
        self.room_dropdown.blockSignals(True)
        self.room_dropdown.clear()
        self.room_dropdown.blockSignals(False)

        # clear beds UI
        while self.beds_container.count():
            self.beds_container.takeAt(0).widget().deleteLater()

        # 🔴 CLEAR FORM FIELDS (THIS WAS MISSING)
        self.customer_box.setCurrentIndex(-1)
        self.customer_box.setEditText("")

        self.passport_entry.clear()
        self.contact_entry.clear()


        # reset dates
        self.checkin.setDate(QDate.currentDate())
        self.checkout.setDate(QDate.currentDate().addDays(1))

        # reload data for new branch
        self.load_rooms()
        self.load_customers()



    def refresh(self):
        self.set_branch(self.branch_id)


    def reset_form(self):
        self.selected_bed_id = None
        self.prefilled_bed_id = None

        self.customer_box.setCurrentIndex(-1)
        self.customer_box.setEditText("")

        self.passport_entry.clear()
        self.contact_entry.clear()

        self.total_entry.clear()
        self.paid_entry.clear()
        self.remaining_label.setText(f"{t('remaining')}: 0.00")

        # reset dates
        self.checkin.setDate(QDate.currentDate())
        self.checkout.setDate(QDate.currentDate().addDays(1))

        # reload beds for current room
        self.load_available_beds()

    def load_customers(self):
        self.customer_box.clear()

        customers = api_get(self.app, "/customers/", {"branch_id": self.branch_id})

        for c in customers:
            self.customer_box.addItem(
                c["name"],
                {
                    "passport": c["passport_id"],
                    "contact": c["contact"]
                }
            )

        # ✅ ADD THIS BLOCK
        completer = QCompleter(
            [self.customer_box.itemText(i) for i in range(self.customer_box.count())],
            self
        )
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)

        self.customer_box.setCompleter(completer)

