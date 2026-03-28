from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QComboBox
)
from PySide6.QtCore import Qt
import os
HAS_QT_CHARTS = False
if os.getenv("HMS_NO_QTCHARTS", "0") != "1":
    try:
        from PySide6.QtCharts import (
            QChart, QChartView,
            QBarSeries, QBarSet,
            QBarCategoryAxis, QValueAxis
        )
        HAS_QT_CHARTS = True
    except Exception:
        try:
            from PySide2.QtCharts import (  # type: ignore
                QChart, QChartView,
                QBarSeries, QBarSet,
                QBarCategoryAxis, QValueAxis
            )
            HAS_QT_CHARTS = True
        except Exception:
            HAS_QT_CHARTS = False
            QChart = QChartView = QBarSeries = QBarSet = QBarCategoryAxis = QValueAxis = None  # type: ignore
else:
    QChart = QChartView = QBarSeries = QBarSet = QBarCategoryAxis = QValueAxis = None  # type: ignore

from i18n import t


class YearlyFinancePage(QWidget):
    def __init__(self, branch_id):
        super().__init__()
        self.branch_id = branch_id

        main = QVBoxLayout(self)
        main.setContentsMargins(24, 24, 24, 24)
        main.setSpacing(16)

        # ===== Header =====
        header_row = QHBoxLayout()

        title = QLabel(t("yearly_finance"))
        title.setObjectName("PageTitle")

        self.year_select = QComboBox()
        self.year_select.addItems(
            [str(y) for y in range(2022, 2026)]
        )
        self.year_select.currentTextChanged.connect(self.refresh)

        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(QLabel(t("year")))
        header_row.addWidget(self.year_select)

        main.addLayout(header_row)

        # ===== Chart card =====
        card = QFrame()
        card.setObjectName("ChartCard")

        card_layout = QVBoxLayout(card)

        self.chart = None
        if HAS_QT_CHARTS:
            self.chart = QChart()
            self.chart.setAnimationOptions(QChart.SeriesAnimations)
            self.chart.legend().setVisible(True)

            self.chart_view = QChartView(self.chart)
            self.chart_view.setRenderHint(self.chart_view.renderHints())
            card_layout.addWidget(self.chart_view)
        else:
            card_layout.addWidget(QLabel(t("error")))
        main.addWidget(card, 1)

        self.refresh()

    # ======================
    def set_branch(self, branch_id):
        self.branch_id = branch_id
        self.refresh()

    def refresh(self):
        if not HAS_QT_CHARTS or self.chart is None:
            return
        year = int(self.year_select.currentText())
        data = self.get_data(year)

        self.chart.removeAllSeries()

        income = QBarSet(t("income"))
        expense = QBarSet(t("expense"))

        for m in data:
            income.append(m["income"])
            expense.append(m["expense"])

        series = QBarSeries()
        series.append(income)
        series.append(expense)

        self.chart.addSeries(series)

        months = [t(m) for m in [
            "jan","feb","mar","apr","may","jun",
            "jul","aug","sep","oct","nov","dec"
        ]]

        axis_x = QBarCategoryAxis()
        axis_x.append(months)

        axis_y = QValueAxis()
        axis_y.setTitleText(t("amount"))

        self.chart.setAxisX(axis_x, series)
        self.chart.setAxisY(axis_y, series)

        self.chart.setTitle(f"{t('yearly_finance')} — {year}")

    # ===== Dummy data =====
    def get_data(self, year):
        return [
            {"income": 1200000, "expense": 800000},
            {"income": 1000000, "expense": 700000},
            {"income": 1400000, "expense": 900000},
            {"income": 1600000, "expense": 1000000},
            {"income": 1800000, "expense": 1100000},
            {"income": 2000000, "expense": 1300000},
            {"income": 2200000, "expense": 1500000},
            {"income": 2100000, "expense": 1400000},
            {"income": 1900000, "expense": 1200000},
            {"income": 1700000, "expense": 1000000},
            {"income": 1500000, "expense": 900000},
            {"income": 1300000, "expense": 850000},
        ]
