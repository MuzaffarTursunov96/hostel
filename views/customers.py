from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QScrollArea, QFrame, QPushButton, QMessageBox, QDialog, QFormLayout, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer

from i18n import t
from .api_client import api_get, api_put, api_delete


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
        self.list_layout.setSpacing(6)
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
        self.list_layout.addStretch()
    
    def refresh(self):
        self.load()


    def add_row(self, c):
        row = QFrame()
        row.setObjectName("TableRow")

        row.customer_id = c["id"]
        row.customer_name = c["name"].lower()
        row.passport_id = (c["passport_id"] or "").lower()
        row.contact = (c["contact"] or "").lower()

        hl = QHBoxLayout(row)
        hl.setContentsMargins(12, 6, 12, 6)
        row.setFixedHeight(40)
        row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
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

        # ✏️ EDIT BUTTON
        btn_edit = QPushButton("✏️")
        btn_edit.setFixedWidth(36)
        btn_edit.clicked.connect(
            lambda _, cust=c: self.edit_customer(cust)
        )

        # 🗑 DELETE BUTTON
        btn_delete = QPushButton("🗑")
        btn_delete.setFixedWidth(36)
        btn_delete.clicked.connect(
            lambda _, cid=c["id"]: self.delete_customer(cid)
        )

        hl.addWidget(btn_edit)
        hl.addWidget(btn_delete)

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

    
    def edit_customer(self, customer):
        dlg = QDialog(self)
        dlg.setWindowTitle(t("edit_customer"))

        form = QFormLayout(dlg)

        name = QLineEdit(customer["name"])
        passport = QLineEdit(customer.get("passport_id") or "")
        contact = QLineEdit(customer.get("contact") or "")

        form.addRow(t("customer"), name)
        form.addRow(t("passport_id"), passport)
        form.addRow(t("phone"), contact)

        btn_save = QPushButton(t("save"))
        btn_cancel = QPushButton(t("cancel"))

        btn_save.clicked.connect(lambda: self.save_customer(
            dlg,
            customer["id"],
            name.text(),
            passport.text(),
            contact.text()
        ))


        btn_cancel.clicked.connect(dlg.reject)

        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(btn_cancel)
        actions.addWidget(btn_save)

        form.addRow(actions)

        dlg.exec()


    def save_customer(self, dlg, customer_id, name, passport_id, contact):
        if not name.strip():
            QMessageBox.warning(
                self,
                t("error"),
                t("name_required")
            )
            return

        try:
            api_put(
                self.app,
                f"/customers/{customer_id}",
                params={
                    "name": name,
                    "contact": contact,
                    "passport_id": passport_id
                }
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                t("error"),
                str(e)
            )
            return

        dlg.accept()
        self.refresh()

    def delete_customer(self, customer_id):
        confirm = QMessageBox.question(
            self,
            t("delete_customer"),
            t("delete_customer_confirm"),
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        try:
            api_delete(
                self.app,
                f"/customers/{customer_id}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                t("error"),
                str(e)
            )
            return

        self.refresh()
