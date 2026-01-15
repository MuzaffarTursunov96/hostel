from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QScrollArea, QWidget, QFrame, QPushButton
)
from PySide6.QtCore import Qt

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

                print(r.keys())



                btn_cancel = QPushButton(t("cancel"))
                btn_cancel.clicked.connect(
                    lambda _, bid=r["id"]: self.cancel_booking(bid)
                )

                actions.addWidget(btn_edit)
                actions.addWidget(btn_cancel)

                rl.addLayout(actions)
                rl.addStretch()

                body_layout.addWidget(row)


        scroll.setWidget(body)
        card_layout.addWidget(scroll)

        main.addWidget(card)
    def edit_booking(self, booking):
        from .active_bookings import EditBookingDialog

        EditBookingDialog(
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
