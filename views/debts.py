from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QPushButton,
    QScrollArea, QLineEdit,
    QDateEdit, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QCursor


from datetime import date, datetime
from i18n import t
from .api_client import api_get, api_post




class DebtsPage(QWidget):
    def __init__(self, app, branch_id):
        super().__init__()

        self.app = app
        self.branch_id = branch_id
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self.apply_customer_filter)

        self.build_ui()
        self.set_default_range()
        self.refresh()


    def build_ui(self):
        main = QVBoxLayout(self)

        title = QLabel(t("debt_analytics"))
        title.setStyleSheet("font-size:26px;font-weight:600;")
        main.addWidget(title)

        # ===== FILTER =====
        filter_box = QFrame()
        fl = QHBoxLayout(filter_box)

        self.from_date = QDateEdit()
        self.to_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.to_date.setCalendarPopup(True)

        btn = QPushButton(t("confirm"))
        btn.clicked.connect(self.refresh)
        btn.setCursor(QCursor(Qt.PointingHandCursor))

        fl.addWidget(QLabel(t("from")))
        fl.addWidget(self.from_date)
        fl.addWidget(QLabel(t("to")))
        fl.addWidget(self.to_date)
        fl.addWidget(btn)
        fl.addStretch()

        main.addWidget(filter_box)

        

        # ===== TABLE =====
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.container = QWidget()
        self.table = QVBoxLayout(self.container)
        self.table.setSpacing(6)
        self.table.setContentsMargins(0, 0, 0, 0)

        self.scroll.setWidget(self.container)
        main.addWidget(self.scroll, 1)


    def set_default_range(self):
        today = date.today()
        self.from_date.setDate(QDate(today.year, 1, 1))
        self.to_date.setDate(QDate.currentDate().addMonths(3))


    def draw_header(self):
        header = QFrame()
        hl = QVBoxLayout(header)

        titles = [
            "customer", "passport_id", "room", "bed",
            "checkin_date", "checkout_date",
            "remaining_amount", "pay_amount", "action"
        ]
        widths = [160, 90, 50, 50, 100, 100, 110, 100, 80]

        row1 = QHBoxLayout()
        for t_key, w in zip(titles, widths):
            lbl = QLabel(t(t_key))
            lbl.setFixedWidth(w)
            lbl.setStyleSheet("font-weight:600;")
            row1.addWidget(lbl)
        hl.addLayout(row1)

        # search
        row2 = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(t("search_customer"))
        self.search.setFixedWidth(widths[0])
        self.search.textChanged.connect(
            lambda: self._search_timer.start(300)
        )
        row2.addWidget(self.search)
        row2.addStretch()
        hl.addLayout(row2)

        self.table.addWidget(header)


    def refresh(self):
        while self.table.count():
            w = self.table.takeAt(0).widget()
            if w:
                w.deleteLater()

        f = self.from_date.date().toPython()
        t_d = self.to_date.date().toPython()

        summary = api_get(
            self.app,
            "/debts/summary",
            {
                "branch_id": self.branch_id,
                "from_date": f.isoformat(),
                "to_date": t_d.isoformat()
            }
        )

      

        debts = api_get(
            self.app,
            "/debts/",
            {
                "branch_id": self.branch_id,
                "from_date": f.isoformat(),
                "to_date": t_d.isoformat()
            }
        )

        if not debts:
            self.table.addWidget(
                QLabel(t("no_unpaid_debts_in_selected_range"))
            )
            return

        self.draw_header()
        for d in debts:
            self.add_row(d)
        self.table.addStretch()



    def add_row(self, d):
        row = QFrame()
        row.setObjectName("ListRow")
        row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        row.setFixedHeight(80)
        row.customer_name = d["customer_name"]
        row.passport_id = d["passport_id"]

        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        values = [
            d["customer_name"],
            d["passport_id"],
            str(d["room_number"]),
            str(d["bed_number"]),
            self.format_date(d["checkin_date"]),
            self.format_date(d["checkout_date"]),
            self.fmt_money(d["remaining_amount"])
        ]

        widths = [160, 90, 50, 50, 100, 100, 110]

        for v, w in zip(values, widths):
            lbl = QLabel(v)
            lbl.setFixedWidth(w)
            layout.addWidget(lbl)

        entry = QLineEdit()
        entry.setPlaceholderText(t("amount"))
        entry.setFixedWidth(100)
        layout.addWidget(entry)

        btn = QPushButton(t("pay"))
        btn.clicked.connect(lambda: self.pay_debt(d, entry))
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        layout.addWidget(btn)

        self.table.addWidget(row)


    def pay_debt(self, d, entry):
        try:
            val = float(entry.text())
            if val <= 0:
                raise ValueError

            api_post(
                self.app,
                "/debts/pay",
                {
                    "branch_id": self.branch_id,
                    "booking_id": d["id"],
                    "amount": val,
                    "paid_by": t("admin")
                }
            )

            QMessageBox.information(
                self, t("success"), t("payment_recorded")
            )

            self.refresh()
            self.refresh_dashboard()

        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))


    def refresh_dashboard(self):
        if "dashboard" in self.app.pages:
            self.app.pages["dashboard"].refresh()

    def set_branch(self, branch_id):
        if self.branch_id == branch_id:
            return
        self.branch_id = branch_id
        self.refresh()

    def apply_customer_filter(self):
        query = self.search.text().strip().lower()

        for i in range(1, self.table.count()):
            row = self.table.itemAt(i).widget()
            if not hasattr(row, "customer_name"):
                continue

            name = row.customer_name.lower()
            passport = row.passport_id.lower()

            row.setVisible(
                not query or query in name or query in passport
            )

    def format_date(self, d):
        if isinstance(d, str):
            d = datetime.fromisoformat(d)
        return d.strftime("%d %b %Y")

    def fmt_money(self, x):
        try:
            return f"{int(x):,}".replace(",", " ")
        except:
            return str(x)
