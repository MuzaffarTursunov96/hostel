from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget,
    QTableWidgetItem, QLabel, QHBoxLayout, QComboBox
)
from PySide6.QtCore import Qt, QDate

from i18n import t
from .api_client import api_get


class ExpensesTableDialog(QDialog):
    def __init__(self, parent, app, branch_id, year=None, month=None):
        super().__init__(parent)

        self.app = app
        self.branch_id = branch_id

        today = QDate.currentDate()
        self.year = year or today.year()
        self.month = month or today.month()

        self.setWindowTitle(t("expense_history"))
        self.resize(800, 450)
        self.setWindowModality(Qt.ApplicationModal)

        layout = QVBoxLayout(self)

        # ---------- TITLE ----------
        title = QLabel(t("expense_history"))
        title.setStyleSheet("font-size:18px;font-weight:600;")
        layout.addWidget(title)

        # ---------- FILTERS ----------
        filter_layout = QHBoxLayout()

        self.month_cb = QComboBox()
        self.year_cb = QComboBox()

        months = [
            "Jan","Feb","Mar","Apr","May","Jun",
            "Jul","Aug","Sep","Oct","Nov","Dec"
        ]

        for i, m in enumerate(months, start=1):
            self.month_cb.addItem(m, i)

        for y in range(today.year() - 5, today.year() + 6):
            self.year_cb.addItem(str(y), y)

        self.month_cb.setCurrentIndex(self.month - 1)
        self.year_cb.setCurrentText(str(self.year))

        self.month_cb.currentIndexChanged.connect(self.on_filter_change)
        self.year_cb.currentIndexChanged.connect(self.on_filter_change)

        filter_layout.addWidget(self.month_cb)
        filter_layout.addWidget(self.year_cb)
        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # ---------- TABLE ----------
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            t("date"),
            t("title"),
            t("category"),
            t("amount")
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        layout.addWidget(self.table)

        self.load_data()

    # ---------- EVENTS ----------
    def on_filter_change(self):
        self.month = self.month_cb.currentData()
        self.year = self.year_cb.currentData()
        self.load_data()

    # ---------- DATA ----------
    def load_data(self):
        rows = api_get(
            self.app,
            "/payments/expenses",
            {
                "branch_id": self.branch_id,
                "year": self.year,
                "month": self.month
            }
        )

        self.table.setRowCount(0)

        if not rows:
            return

        self.table.setRowCount(len(rows))

        for r, e in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(str(e["expense_date"])))
            self.table.setItem(r, 1, QTableWidgetItem(e["title"]))
            self.table.setItem(r, 2, QTableWidgetItem(e["category"] or "-"))
            self.table.setItem(r, 3, QTableWidgetItem(f'{e["amount"]:,}'))
