from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QMessageBox, QCheckBox,
    QDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QInputDialog
)
from PySide6.QtCore import Qt
from requests.exceptions import HTTPError
from PySide6.QtGui import QCursor

from .api_client import api_get, api_post,api_delete


# =========================
# ROOT ADMIN PANEL
# =========================

class RootAdminPanel(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.setWindowTitle("Root Admin Panel")
        self.resize(900, 600)

        self.tabs = QTabWidget()

        self.admins_tab = AdminsTab(app)
        self.branches_tab = BranchesTab(app)
        self.licenses_tab = LicensesTab(app)

        self.tabs.addTab(self.admins_tab, "Admins")
        self.tabs.addTab(self.branches_tab, "Branches")
        self.tabs.addTab(self.licenses_tab, "Licenses")

        self.tabs.currentChanged.connect(self.on_tab_change)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)

    def on_tab_change(self, index):
        widget = self.tabs.widget(index)
        if hasattr(widget, "load"):
            widget.load()



# =========================
# ADMINS TAB
# =========================

class AdminsTab(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Telegram ID", "Username",
            "Active", "Branches", "Actions"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)

        self.add_btn = QPushButton("➕ Add Admin")
        self.add_btn.clicked.connect(self.add_admin)
        self.add_btn.setCursor(QCursor(Qt.PointingHandCursor))

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addWidget(self.add_btn)

        self.load_admins()

    # ---------- LOAD ----------
    def load_admins(self):
        self.table.setRowCount(0)
        admins = api_get(self.app, "/root/admins")

        if not isinstance(admins, list):
            QMessageBox.critical(
                self,
                "API Error",
                f"/root/admins returned invalid data:\n{admins}"
            )
            return

        for admin in admins:
            row = self.table.rowCount()
            self.table.insertRow(row)

            uid = admin["id"]

            self.table.setItem(row, 0, QTableWidgetItem(str(uid)))
            self.table.setItem(row, 1, QTableWidgetItem(str(admin["telegram_id"])))
            self.table.setItem(row, 2, QTableWidgetItem(admin.get("username") or ""))

            chk = QCheckBox()
            chk.setChecked(admin["is_active"])
            chk.stateChanged.connect(
                lambda state, u=uid: self.toggle_active(u, state)
            )
            self.table.setCellWidget(row, 3, chk)

            self.table.setItem(
                row, 4,
                QTableWidgetItem(", ".join(map(str, admin["branches"])))
            )

            actions = QWidget()
            hl = QHBoxLayout(actions)
            hl.setContentsMargins(0, 0, 0, 0)

            reset_btn = QPushButton("🔑 Reset")
            reset_btn.clicked.connect(lambda _, u=uid: self.reset_password(u))
            reset_btn.setCursor(QCursor(Qt.PointingHandCursor))

            branch_btn = QPushButton("🏢 Branches")
            branch_btn.clicked.connect(lambda _, u=uid: self.assign_branches(u))
            branch_btn.setCursor(QCursor(Qt.PointingHandCursor))

            delete_btn = QPushButton("🗑 Delete")
            delete_btn.clicked.connect(lambda _, u=uid: self.delete_admin(u))
            delete_btn.setCursor(QCursor(Qt.PointingHandCursor))


            hl.addWidget(reset_btn)
            hl.addWidget(branch_btn)
            hl.addWidget(delete_btn)

            self.table.setCellWidget(row, 5, actions)

    # ---------- ACTIONS ----------
    def toggle_active(self, user_id, state):
        api_post(self.app, f"/root/admins/{user_id}/set-active", {
            "is_active": bool(state)
        })

    def delete_admin(self, user_id):
        reply = QMessageBox.question(
            self,
            "Confirm delete",
            "Delete this admin permanently?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            api_delete(self.app, f"/root/admins/{user_id}")
            self.load_admins()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


    def reset_password(self, user_id):
        pwd, ok = PasswordDialog.get(self)
        if not ok or not pwd:
            return

        api_post(self.app, f"/root/admins/{user_id}/password", {
            "password": pwd
        })
        QMessageBox.information(self, "Success", "Password updated")

    def assign_branches(self, user_id):
        dlg = AssignBranchesDialog(self.app, user_id, self)
        if dlg.exec():
            self.load_admins()

    def add_admin(self):
        dlg = AddAdminDialog(self.app, self)
        if dlg.exec():
            self.load_admins()


# =========================
# ADD ADMIN DIALOG
# =========================

class AddAdminDialog(QDialog):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app

        self.setWindowTitle("Add Admin")
        self.resize(300, 200)

        layout = QVBoxLayout(self)

        self.telegram = QLineEdit()
        self.telegram.setPlaceholderText("Telegram ID")

        self.username = QLineEdit()
        self.username.setPlaceholderText("Username (optional)")

        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)

        save = QPushButton("Create")
        save.clicked.connect(self.save)
        save.setCursor(QCursor(Qt.PointingHandCursor))

        layout.addWidget(QLabel("Telegram ID"))
        layout.addWidget(self.telegram)
        layout.addWidget(QLabel("Username"))
        layout.addWidget(self.username)
        layout.addWidget(QLabel("Password"))
        layout.addWidget(self.password)
        layout.addWidget(save)

    def save(self):
        if not self.telegram.text() or not self.password.text():
            QMessageBox.warning(self, "Error", "Telegram ID and password required")
            return

        try:
            api_post(self.app, "/root/admins", {
                "telegram_id": int(self.telegram.text()),
                "username": self.username.text(),
                "password": self.password.text()
            })
        except HTTPError as e:
            # 🔥 SHOW BACKEND ERROR MESSAGE
            try:
                error_json = e.response.json()
                message = error_json.get("detail", "Unknown error")
            except Exception:
                message = str(e)

            QMessageBox.critical(
                self,
                "Create admin failed",
                message
            )
            return  # ❗ do NOT close dialog

        QMessageBox.information(
            self,
            "Success",
            "Admin created successfully"
        )
        self.accept()


# =========================
# ASSIGN BRANCHES
# =========================

class AssignBranchesDialog(QDialog):
    def __init__(self, app, user_id, parent=None):
        super().__init__(parent)
        self.app = app
        self.user_id = user_id

        self.setWindowTitle("Assign Branches")
        self.resize(300, 400)

        layout = QVBoxLayout(self)

        self.list = QListWidget()

        branches = api_get(app, "/branches/")
        admin = api_get(app, f"/root/admins/{user_id}")
        current = set(admin["branches"])

        for b in branches:
            item = QListWidgetItem(b["name"])
            item.setData(Qt.UserRole, b["id"])
            item.setCheckState(
                Qt.Checked if b["id"] in current else Qt.Unchecked
            )
            self.list.addItem(item)

        save = QPushButton("Save")
        save.clicked.connect(self.save)
        save.setCursor(QCursor(Qt.PointingHandCursor))

        layout.addWidget(self.list)
        layout.addWidget(save)

    def save(self):
        selected = []
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.data(Qt.UserRole))

        api_post(self.app, f"/root/admins/{self.user_id}/branches", {
            "branch_ids": selected
        })

        self.accept()


# =========================
# PASSWORD DIALOG
# =========================

class PasswordDialog:
    @staticmethod
    def get(parent):
        return QInputDialog.getText(
            parent,
            "New Password",
            "Enter new password",
            QLineEdit.Password
        )



# =========================
# BRANCHES TAB
# =========================

class BranchesTab(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["ID", "Name"])

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)

        add_btn = QPushButton("➕ Add Branch")
        add_btn.clicked.connect(self.add_branch)
        add_btn.setCursor(QCursor(Qt.PointingHandCursor))

        del_btn = QPushButton("🗑 Delete Branch")
        del_btn.clicked.connect(self.delete_branch)
        del_btn.setCursor(QCursor(Qt.PointingHandCursor))

        layout.addWidget(add_btn)
        layout.addWidget(del_btn)


        self.load()

    def load(self):
        self.table.setRowCount(0)
        for b in api_get(self.app, "/branches/"):
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(b["id"])))
            self.table.setItem(r, 1, QTableWidgetItem(b["name"]))


    def add_branch(self):
        name, ok = QInputDialog.getText(
            self, "New Branch", "Branch name"
        )
        if ok and name.strip():
            api_post(self.app, "/root/branches", {"name": name})
            self.load()

    def delete_branch(self):
        row = self.table.currentRow()
        if row < 0:
            return

        branch_id = int(self.table.item(row, 0).text())

        reply = QMessageBox.question(
            self,
            "Confirm",
            "Delete branch permanently?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        api_delete(self.app, f"/root/branches/{branch_id}")

        self.load()

# =========================
# LICENSES TAB
# =========================

class LicensesTab(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app

        layout = QVBoxLayout(self)

        # ---- Trial checkbox ----
        self.trial_chk = QCheckBox("Trial license")
        self.trial_days = QLineEdit()
        self.trial_days.setPlaceholderText("Trial days (e.g. 7)")
        self.trial_days.setEnabled(False)

        self.trial_chk.stateChanged.connect(
            lambda s: self.trial_days.setEnabled(bool(s))
        )

        # ---- Generate button ----
        self.gen_btn = QPushButton("🔑 Generate License")
        self.gen_btn.clicked.connect(self.generate)
        self.gen_btn.setCursor(QCursor(Qt.PointingHandCursor))

        # ---- Output ----
        self.output = QLineEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Generated license will appear here")

        layout.addWidget(self.trial_chk)
        layout.addWidget(self.trial_days)
        layout.addWidget(self.gen_btn)
        layout.addWidget(QLabel("License key"))
        layout.addWidget(self.output)

    def generate(self):
        is_trial = self.trial_chk.isChecked()
        days = self.trial_days.text().strip()

        payload = {
            "is_trial": is_trial,
            "trial_days": int(days) if is_trial and days else None
        }

        try:
            res = api_post(self.app, "/license/admin/create-license", payload)
            self.output.setText(res["license_key"])

            QMessageBox.information(
                self,
                "Success",
                "License generated successfully"
            )

        except HTTPError as e:
            try:
                msg = e.response.json().get("detail", str(e))
            except Exception:
                msg = str(e)

            QMessageBox.critical(self, "Error", msg)
