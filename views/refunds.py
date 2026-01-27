from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QPushButton,
    QScrollArea, QDateEdit
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QCursor
from datetime import date, datetime

from i18n import t
from .api_client import api_get


class RefundsPage(QWidget):
    def __init__(self, app, branch_id):
        super().__init__()

        self.app = app
        self.branch_id = branch_id

        self.build_ui()
        self.set_default_range()
        self.refresh()


    def build_ui(self):
        main = QVBoxLayout(self)

        title = QLabel(t("refunds"))
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
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.clicked.connect(self.refresh)

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

        self.scroll.setWidget(self.container)
        main.addWidget(self.scroll, 1)


    def set_default_range(self):
        today = date.today()
        self.from_date.setDate(QDate(today.year, today.month, 1))
        self.to_date.setDate(QDate.currentDate())


    def draw_header(self):
        header = QFrame()
        hl = QHBoxLayout(header)

        titles = [
            "booking_id",
            "refund_amount",
            "refund_reason",
            "date"
        ]
        widths = [100, 140, 300, 140]

        for key, w in zip(titles, widths):
            lbl = QLabel(t(key))
            lbl.setFixedWidth(w)
            lbl.setStyleSheet("font-weight:600;")
            hl.addWidget(lbl)

        hl.addStretch()
        self.table.addWidget(header)


    def refresh(self):
        while self.table.count():
            w = self.table.takeAt(0).widget()
            if w:
                w.deleteLater()

        f = self.from_date.date().toPython()
        t_d = self.to_date.date().toPython()

        refunds = api_get(
            self.app,
            "/refunds/list",
            {
                "branch_id": self.branch_id,
                "from_date": f.isoformat(),
                "to_date": t_d.isoformat()
            }
        )

        if not refunds:
            self.table.addWidget(QLabel(t("no_refunds_in_selected_range")))
            return

        self.draw_header()
        for r in refunds:
            self.add_row(r)


    def add_row(self, r):
        row = QFrame()
        layout = QHBoxLayout(row)

        values = [
            f"#{r['booking_id']}",
            self.fmt_money(r["refund_amount"]),
            r.get("refund_reason", ""),
            self.format_date(r["created_at"])
        ]

        widths = [100, 140, 300, 140]

        for v, w in zip(values, widths):
            lbl = QLabel(v)
            lbl.setFixedWidth(w)
            layout.addWidget(lbl)

        layout.addStretch()
        self.table.addWidget(row)


    def format_date(self, d):
        if isinstance(d, str):
            d = datetime.fromisoformat(d)
        return d.strftime("%d %b %Y")

    def fmt_money(self, x):
        try:
            return f"{int(x):,}".replace(",", " ")
        except:
            return str(x)
