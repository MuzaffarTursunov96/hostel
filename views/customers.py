from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, QTimer

from i18n import t
from .api_client import api_get


COL_WIDTHS = [260, 200, 200]


class CustomersPage(QWidget):
    def __init__(self, app, branch_id):
        super().__init__()

        self.app = app
        self.branch_id = branch_id

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.apply_filter)

        self.build_ui()
        self.load()

    # ================= UI =================
    def build_ui(self):
        main = QVBoxLayout(self)
        main.setSpacing(14)

        # ===== TITLE =====
        title = QLabel(t("customers"))
        title.setStyleSheet("font-size:22px;font-weight:600;")
        main.addWidget(title)

        # ===== SEARCH =====
        search_row = QHBoxLayout()

        self.search = QLineEdit()
        self.search.setPlaceholderText(t("search_customer"))
        self.search.textChanged.connect(
            lambda: self.search_timer.start(300)
        )

        search_row.addWidget(self.search)
        search_row.addStretch()
        main.addLayout(search_row)

        # ===== TABLE HEADER =====
        header = QFrame()
        header.setObjectName("TableHeader")

        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 8, 12, 8)

        headers = [
            t("customer"),
            t("passport_id"),
            t("phone")
        ]

        for text, w in zip(headers, COL_WIDTHS):
            lbl = QLabel(text)
            lbl.setFixedWidth(w)
            lbl.setStyleSheet("font-weight:600;")
            hl.addWidget(lbl)

        hl.addStretch()
        main.addWidget(header)

        # ===== TABLE BODY =====
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.container = QWidget()
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setSpacing(2)
        self.list_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll.setWidget(self.container)
        main.addWidget(self.scroll)

    # ================= DATA =================
    def load(self):
        while self.list_layout.count():
            w = self.list_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        customers = api_get(
            self.app,
            "/customers/",
            {"branch_id": self.branch_id}
        )

        if not customers:
            lbl = QLabel(t("no_customers"))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("padding:20px;color:#6b7280;")
            self.list_layout.addWidget(lbl)
            return

        for c in customers:
            self.add_row(c)
    
    def refresh(self):
        self.load()


    def add_row(self, c):
        row = QFrame()
        row.setObjectName("TableRow")

        row.customer_name = c["name"].lower()
        row.passport_id = (c["passport_id"] or "").lower()
        row.contact = (c["contact"] or "").lower()

        hl = QHBoxLayout(row)
        hl.setContentsMargins(12, 6, 12, 6)
        row.setFixedHeight(40)

        hl.setSpacing(0)

        values = [
            c["name"],
            c["passport_id"] or "—",
            c["contact"] or "—"
        ]

        for v, w in zip(values, COL_WIDTHS):
            lbl = QLabel(v)
            lbl.setFixedWidth(w)
            hl.addWidget(lbl)

        hl.addStretch()
        self.list_layout.addWidget(row)

    # ================= SEARCH =================
    def apply_filter(self):
        q = self.search.text().strip().lower()

        for i in range(self.list_layout.count()):
            row = self.list_layout.itemAt(i).widget()
            if not hasattr(row, "customer_name"):
                continue

            row.setVisible(
                not q
                or q in row.customer_name
                or q in row.passport_id
                or q in row.contact
            )

    # ================= UTILS =================
    def set_branch(self, branch_id):
        self.branch_id = branch_id
        self.load()
