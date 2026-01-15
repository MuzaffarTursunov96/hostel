from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QScrollArea,
    QComboBox, QLineEdit, QPushButton
)
from PySide6.QtCore import Qt, QTimer
from datetime import date, datetime

from .api_client import api_get
from i18n import t



class PaymentHistoryDialog(QDialog):
    def __init__(self, parent, app, branch_id):
        super().__init__(parent)

        self.app = app
        self.branch_id = branch_id

        self.setWindowTitle(t("payment_history"))
        self.resize(1200, 500)
        self.setModal(True)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.apply_customer_filter)

        main = QVBoxLayout(self)

        # ================= FILTER =================
        filter_card = QFrame()
        filter_layout = QHBoxLayout(filter_card)

        today = date.today()

        self.month = QComboBox()
        self.month.addItems([str(i) for i in range(1, 13)])
        self.month.setCurrentText(str(today.month))

        self.year = QComboBox()
        self.year.addItems(
            [str(y) for y in range(today.year, today.year + 6)]
        )
        self.year.setCurrentText(str(today.year))

        load_btn = QPushButton(t("load"))
        load_btn.clicked.connect(self.load)

        filter_layout.addWidget(QLabel(t("month")))
        filter_layout.addWidget(self.month)
        filter_layout.addWidget(QLabel(t("year")))
        filter_layout.addWidget(self.year)
        filter_layout.addWidget(load_btn)
        filter_layout.addStretch()

        main.addWidget(filter_card)

        # ================= TABLE =================
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.container = QFrame()
        self.table = QVBoxLayout(self.container)
        self.table.setSpacing(6)

        self.scroll.setWidget(self.container)
        main.addWidget(self.scroll)

        self.draw_header()
        self.load()


    def draw_header(self):
        header = QFrame()
        header_layout = QVBoxLayout(header)

        titles = [
            "date", "customer", "passport_id",
            "room", "bed", "amount", "paid_by"
        ]
        widths = [160, 200, 100, 80, 80, 120, 120]

        title_row = QHBoxLayout()
        for title, w in zip(titles, widths):
            lbl = QLabel(t(title))
            lbl.setFixedWidth(w)
            lbl.setStyleSheet("font-weight:600;")
            title_row.addWidget(lbl)

        header_layout.addLayout(title_row)

        # -------- search row --------
        search_row = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(t("search_customer"))
        self.search_input.setFixedWidth(widths[1])
        self.search_input.textChanged.connect(
            lambda: self.search_timer.start(300)
        )

        search_row.addWidget(self.search_input)
        search_row.addStretch()

        header_layout.addLayout(search_row)

        self.table.addWidget(header)


    def load(self):
        # remove old rows (keep header)
        while self.table.count() > 1:
            w = self.table.takeAt(1).widget()
            if w:
                w.deleteLater()

        rows = api_get(
            self.app,
            "/payment-history/",
            {
                "branch_id": self.branch_id,
                "year": int(self.year.currentText()),
                "month": int(self.month.currentText())
            }
        )

        if not rows:
            self.table.addWidget(
                QLabel(t("no_payments_for_this_month"))
            )
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

        paid_at = datetime.fromisoformat(
            r["paid_at"]
        ).strftime("%d %b %Y %H:%M")

        values = [
            paid_at,
            r["customer_name"],
            r["passport_id"],
            str(r["room_number"]),
            str(r["bed_number"]),
            f"{r['paid_amount']:.2f}",
            r["paid_by"]
        ]

        widths = [160, 200, 100, 80, 80, 120, 120]

        for v, w in zip(values, widths):
            lbl = QLabel(v)
            lbl.setFixedWidth(w)
            layout.addWidget(lbl)

        self.table.addWidget(row)


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
