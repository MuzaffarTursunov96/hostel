from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QLineEdit, QDateEdit,
    QPushButton
)
from PySide6.QtCore import Qt, QDate
from datetime import datetime

from i18n import t
from .api_client import api_get


class BookingHistoryPage(QDialog):
    def __init__(self, app, branch_id):
        super().__init__()

        self.app = app
        self.branch_id = branch_id
        self.rows = []  # 🔥 STORE ROW WIDGETS

        self.setWindowTitle(t("booking_history"))
        self.resize(1200, 550)
        self.setModal(True)

        main = QVBoxLayout(self)
        main.setSpacing(12)

        # ================= TITLE =================
        title = QLabel("📜 " + t("booking_history"))
        title.setObjectName("PageTitle")
        main.addWidget(title)

        # ================= FILTERS =================
        filters = QHBoxLayout()
        filters.setSpacing(8)

        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(QDate.currentDate().addMonths(-1))

        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(QDate.currentDate())

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(t("search_customer"))
        self.search_input.setFixedWidth(260)

        # 🔥 LIVE FILTER (OLD LOGIC)
        self.search_input.textChanged.connect(self.apply_customer_filter)
        self.search_input.returnPressed.connect(self.load)

        btn_filter = QPushButton("🔍 " + t("filter"))
        btn_filter.clicked.connect(self.load)

        btn_reset = QPushButton(t("reset"))
        btn_reset.clicked.connect(self.reset_filters)

        filters.addWidget(QLabel(t("from")))
        filters.addWidget(self.from_date)

        filters.addWidget(QLabel(t("to")))
        filters.addWidget(self.to_date)

        filters.addWidget(self.search_input)
        filters.addWidget(btn_filter)
        filters.addWidget(btn_reset)
        filters.addStretch()

        main.addLayout(filters)

        # ================= TABLE =================
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.container = QFrame()
        self.table = QVBoxLayout(self.container)
        self.table.setSpacing(2)

        self.scroll.setWidget(self.container)
        main.addWidget(self.scroll)

        self.draw_header()
        self.load()

    # ================= HEADER =================
    def draw_header(self):
        header = QFrame()
        header.setObjectName("ListCard")

        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 8, 12, 8)
        hl.setSpacing(20)

        columns = [
            ("customer", 180, Qt.AlignLeft),
            ("passport_id", 120, Qt.AlignLeft),
            ("room", 60, Qt.AlignCenter),
            ("bed", 60, Qt.AlignCenter),
            ("checkin_date", 120, Qt.AlignCenter),
            ("checkout_date", 120, Qt.AlignCenter),
            ("total_amount", 120, Qt.AlignRight),
        ]

        for key, w, align in columns:
            lbl = QLabel(t(key))
            lbl.setFixedWidth(w)
            lbl.setAlignment(align | Qt.AlignVCenter)
            lbl.setStyleSheet("font-weight:600;")
            hl.addWidget(lbl)

        self.table.addWidget(header)

    # ================= LOAD DATA (NEW LOGIC) =================
    def load(self):
        # clear old rows
        self.rows.clear()
        while self.table.count() > 1:
            w = self.table.takeAt(1).widget()
            if w:
                w.deleteLater()

        rows = api_get(
            self.app,
            "/booking-history/",
            {
                "branch_id": self.branch_id,
                "from_date": self.from_date.date().toString("yyyy-MM-dd"),
                "to_date": self.to_date.date().toString("yyyy-MM-dd"),
            }
        )

        if not rows:
            self.table.addWidget(QLabel(t("no_bookings")))
            return

        for r in rows:
            self.add_row(r)

        # 🔥 APPLY LIVE FILTER AFTER LOAD
        self.apply_customer_filter()

    # ================= ROW =================
    def add_row(self, r):
        row = QFrame()
        row.setObjectName("ListRow")

        # store searchable data
        row.customer_name = (r["customer_name"] or "").lower()
        row.passport_id = (r["passport_id"] or "").lower()

        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(20)

        def cell(text, width, align=Qt.AlignLeft):
            lbl = QLabel(text)
            lbl.setFixedWidth(width)
            lbl.setAlignment(align | Qt.AlignVCenter)
            return lbl

        layout.addWidget(cell(r["customer_name"], 180))
        layout.addWidget(cell(r["passport_id"], 120))
        layout.addWidget(cell(str(r["room_number"]), 60, Qt.AlignCenter))
        layout.addWidget(cell(str(r["bed_number"]), 60, Qt.AlignCenter))
        layout.addWidget(cell(self.format_date(r["checkin_date"]), 120, Qt.AlignCenter))
        layout.addWidget(cell(self.format_date(r["checkout_date"]), 120, Qt.AlignCenter))
        layout.addWidget(cell(f"{r['total_amount']:.2f}", 120, Qt.AlignRight))

        self.table.addWidget(row)
        self.rows.append(row)  # 🔥 SAVE ROW

    # ================= LIVE FILTER (OLD LOGIC) =================
    def apply_customer_filter(self):
        query = self.search_input.text().strip().lower()

        for row in self.rows:
            row.setVisible(
                not query
                or query in row.customer_name
                or query in row.passport_id
            )

    # ================= RESET =================
    def reset_filters(self):
        self.from_date.setDate(QDate.currentDate().addMonths(-1))
        self.to_date.setDate(QDate.currentDate())
        self.search_input.clear()
        self.load()

    # ================= HELPERS =================
    def format_date(self, d):
        if isinstance(d, str):
            d = datetime.fromisoformat(d)
        return d.strftime("%d %b %Y")
