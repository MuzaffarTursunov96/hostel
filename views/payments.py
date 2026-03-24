from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame,
    QComboBox, QLineEdit, QMessageBox,QGridLayout
)
from PySide6.QtCore import Qt, QDate,QSize
from PySide6.QtGui import QPainter,QCursor,QIcon

from PySide6.QtCharts import (
    QChart, QChartView, QPieSeries
)

from datetime import date
from i18n import t
from .api_client import api_get, api_post
from .payment_history import PaymentHistoryDialog
from .expenses_table import ExpensesTableDialog
from .refunds import RefundsPage
from .utils import resource_path



class PaymentsPage(QWidget):
    def __init__(self, app, branch_id):
        super().__init__()

        self.app = app
        self.branch_id = branch_id

        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.container = QWidget()
        self.main = QVBoxLayout(self.container)
        self.main.setSpacing(16)

        self.scroll.setWidget(self.container)
        self.outer.addWidget(self.scroll)

        self.build_ui()
        self.refresh()

    # ================= UI =================
    def build_ui(self):
        # ===== TITLE =====
        title = QLabel(t("monthly_finance"))
        title.setStyleSheet("font-size:22px;font-weight:600;")
        self.main.addWidget(title)

        ACTION_BTN_STYLE = """
            QPushButton {
                padding: 4px 14px;
                font-size: 13px;
                border-radius: 8px;
                background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
            }
            QPushButton:hover {
                background-color: #EEF2FF;
                border-color: #C7D2FE;
            }
            QPushButton:pressed {
                background-color: #E0E7FF;
            }
            """

        # ===== FILTER BAR =====
        filter_bar = QHBoxLayout()

        self.month = QComboBox()
        self.month.addItems(
            [
                t("january"), t("february"), t("march"),
                t("april"), t("may"), t("june"),
                t("july"), t("august"), t("september"),
                t("october"), t("november"), t("december")
            ]
        )

        self.year = QComboBox()
        current_year = date.today().year
        for y in range(current_year, current_year + 5):
            self.year.addItem(str(y))

        filter_btn = QPushButton(t("filter"))
        filter_btn.clicked.connect(self.refresh)
        filter_btn.setCursor(QCursor(Qt.PointingHandCursor))

        filter_bar.addWidget(self.month)
        filter_bar.addWidget(self.year)
        filter_bar.addWidget(filter_btn)
        filter_bar.addStretch()

        self.main.addLayout(filter_bar)

        
        cards = QGridLayout()
        cards.setSpacing(14)

        self.card_income = FinanceCard(t("income"), "#E8F7EE")
        self.card_expenses = FinanceCard(t("expenses"), "#FDECEC")
        self.card_debt = FinanceCard(t("debt"), "#FFF7D6")
        self.card_refunds = FinanceCard(t("refunds"), "#EAF2FF")
        self.card_profit = FinanceCard(t("profit"), "#EEF2FF")

        cards.addWidget(self.card_income, 0, 0)
        cards.addWidget(self.card_expenses, 0, 1)
        cards.addWidget(self.card_debt, 1, 0)
        cards.addWidget(self.card_refunds, 1, 1)
        cards.addWidget(self.card_profit, 2, 0, 1, 2)  # full width

        self.main.addLayout(cards)

        # ===== PIE CHART (moved below cards) =====
        chart_wrap = QFrame()
        chart_wrap.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 14px;
            }
        """)
        chart_layout = QVBoxLayout(chart_wrap)
        chart_layout.setContentsMargins(8, 8, 8, 8)

        self.chart = QChart()
        self.chart.legend().setVisible(True)
        self.chart.setAnimationOptions(QChart.SeriesAnimations)

        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.setMinimumHeight(260)

        chart_layout.addWidget(self.chart_view)
        self.main.addWidget(chart_wrap)

        
        

        # ===== ADD EXPENSE =====
        form = QHBoxLayout()
        form.setSpacing(8)

        self.title_inp = QLineEdit()
        self.title_inp.setPlaceholderText(t("title"))
        self.title_inp.setFixedHeight(32)

        self.amount_inp = QLineEdit()
        self.amount_inp.setPlaceholderText(t("amount"))
        self.amount_inp.setFixedWidth(120)
        self.amount_inp.setFixedHeight(32)

        add_btn = QPushButton(t("add"))
        add_btn.setFixedHeight(32)
        add_btn.setCursor(QCursor(Qt.PointingHandCursor))



        add_btn.clicked.connect(self.add_expense)
        add_btn.setCursor(QCursor(Qt.PointingHandCursor))

        form.addWidget(self.title_inp)
        form.addWidget(self.amount_inp)
        form.addWidget(add_btn)

        self.main.addLayout(form)

        # ===== HISTORY =====
        actions = QHBoxLayout()
        actions.setSpacing(8)

        def make_small_btn(text, icon_path, handler):
            btn = QPushButton(text)
            btn.setFixedHeight(32)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setStyleSheet(ACTION_BTN_STYLE)

            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(16, 16))
            btn.setLayoutDirection(Qt.LeftToRight)  # icon before text

            btn.clicked.connect(handler)
            return btn



        history_btn = make_small_btn(
            t("payment_history"),
            resource_path("assets/icons/payments.png"),
            self.open_history
        )

        expenses_btn = make_small_btn(
            t("view_expenses_table"),
            resource_path("assets/icons/expenses.png"),
            self.open_expenses_table
        )

        refunds_btn = make_small_btn(
            t("refunds"),
            resource_path("assets/icons/refunds.png"),
            self.open_refunds
        )


        actions.addWidget(history_btn)
        actions.addWidget(expenses_btn)
        actions.addWidget(refunds_btn)
        actions.addStretch()

        self.main.addLayout(actions)



        # ===== DEFAULT CURRENT MONTH/YEAR =====
        today = date.today()

        self.month.setCurrentIndex(today.month - 1)

        year_index = self.year.findText(str(today.year))
        if year_index >= 0:
            self.year.setCurrentIndex(year_index)

        self.main.addSpacing(24)


    # ================= DATA =================
    def refresh(self):
        month = self.month.currentIndex() + 1
        year = int(self.year.currentText())

        # -------- MONTHLY FINANCE (PIE) --------
        finance = api_get(
            self.app,
            "/payments/monthly-finance",
            {
                "branch_id": self.branch_id,
                "year": year,
                "month": month
            }
        )

        self.draw_pie(finance)
        self.update_cards(finance)

    def open_refunds(self):
        dlg = RefundsPage(self.app, self.branch_id)
        dlg.setMinimumSize(900, 600)
        dlg.exec()




    def update_cards(self, finance: dict):
        income = finance.get("income", 0)
        expenses = finance.get("expenses", 0)
        debt = finance.get("debt", 0)
        refunds = finance.get("refunds", 0)

        profit = income - expenses - refunds

        self.card_income.set_value(income)
        self.card_expenses.set_value(expenses)
        self.card_debt.set_value(debt)
        self.card_refunds.set_value(refunds)
        self.card_profit.set_value(profit)


    def fmt(self, value: float) -> str:
        return f"{value:,.0f}".replace(",", " ")
    

    def open_expenses_table(self):
        month = self.month.currentIndex() + 1
        year = int(self.year.currentText())

        dlg = ExpensesTableDialog(
            self,
            self.app,
            self.branch_id,
            year,
            month
        )
        dlg.exec()



    # ================= PIE =================
    def draw_pie(self, finance: dict):
        self.chart.removeAllSeries()
        series = QPieSeries()

        income = finance.get("income", 0)
        expenses = finance.get("expenses", 0)
        debt = finance.get("debt", 0)
        refunds = finance.get("refunds", 0)

        if income:
            series.append(t("income"), income)
        if expenses:
            series.append(t("expenses"), expenses)
        if refunds:
            series.append(t("refunds"), refunds)
        if debt:
            series.append(t("debt"), debt)

        self.chart.addSeries(series)
        self.chart.setTitle(t("monthly_finance"))

        

    # ================= ACTIONS =================
    def add_expense(self):
        try:
            title = self.title_inp.text().strip()
            amount = float(self.amount_inp.text())

            if not title or amount <= 0:
                raise ValueError(t("invalid_data"))

            api_post(
                self.app,
                "/payments/expense",
                {
                    "branch_id": self.branch_id,
                    "title": title,
                    "category": "other",
                    "amount": amount,
                    "expense_date": QDate.currentDate().toString("yyyy-MM-dd")
                }
            )

            self.title_inp.clear()
            self.amount_inp.clear()
            self.refresh()

        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))

    def open_history(self):
        dlg = PaymentHistoryDialog(self, self.app, self.branch_id)
        dlg.exec()

    def set_branch(self, branch_id):
        self.branch_id = branch_id
        self.refresh()


class FinanceCard(QFrame):
    def __init__(self, title: str, bg_color: str):
        super().__init__()

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 16px;
            }}
        """)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-size:14px; color:#555;")

        self.value_lbl = QLabel("0")
        self.value_lbl.setStyleSheet("font-size:22px; font-weight:700;")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(4)
        layout.addWidget(self.title_lbl)
        layout.addWidget(self.value_lbl)

    def set_value(self, value: float):
        self.value_lbl.setText(f"{value:,.0f}".replace(",", " "))
