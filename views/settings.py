from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
    QMessageBox, QComboBox, QScrollArea, QFrame
)
from PySide6.QtCore import Qt,QSize
from PySide6.QtGui import QCursor,QIcon

from utils.config import load_config, save_config
from i18n import set_lang, t
from .api_client import api_post,api_get







class SettingsPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.branches = []

        self.build_ui()
        self.load_branches()

    def build_ui(self):
        root = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        root.addWidget(scroll)

        container = QWidget()
        self.layout = QVBoxLayout(container)
        scroll.setWidget(container)

        # ===== TITLE =====
        title = self.make_title(
            t("settings"),
            "assets/icons/settings2.png",
            size=24
        )
        self.layout.addWidget(title)


        # ===== BRANCH SECTION =====
        self.build_branch_section()

        # ===== USER SETTINGS =====
        user_lbl = self.make_title(
            t("user_settings"),
            "assets/icons/locked.png",
            size=18
        )
        self.layout.addWidget(user_lbl)


        self.current_password = QLineEdit()
        self.current_password.setEchoMode(QLineEdit.Password)
        self.current_password.setPlaceholderText(t("current_password"))

        self.new_password = QLineEdit()
        self.new_password.setEchoMode(QLineEdit.Password)
        self.new_password.setPlaceholderText(t("new_password"))

        self.confirm_password = QLineEdit()
        self.confirm_password.setEchoMode(QLineEdit.Password)
        self.confirm_password.setPlaceholderText(t("confirm_password"))

        for w in (
            self.current_password,
            self.new_password,
            self.confirm_password
        ):
            self.layout.addWidget(w)

        save_btn = QPushButton(t("save_changes"))
        save_btn.setIcon(QIcon("assets/icons/save.png"))
        save_btn.setIconSize(QSize(16, 16))
        save_btn.clicked.connect(self.change_password)
        self.layout.addWidget(save_btn)
        save_btn.setCursor(QCursor(Qt.PointingHandCursor))

        # ===== LANGUAGE =====
        lang_lbl = self.make_title(
            t("language"),
            "assets/icons/language.png",
            size=18
        )
        self.layout.addWidget(lang_lbl)

        lang_box = QHBoxLayout()

        btn_ru = QPushButton(t("russian"))
        btn_uz = QPushButton(t("uzbek"))

        btn_ru.clicked.connect(lambda: self.switch_lang("ru"))
        btn_uz.clicked.connect(lambda: self.switch_lang("uz"))
        btn_ru.setCursor(QCursor(Qt.PointingHandCursor))
        btn_uz.setCursor(QCursor(Qt.PointingHandCursor))

        lang_box.addWidget(btn_ru)
        lang_box.addWidget(btn_uz)

        self.layout.addLayout(lang_box)
        self.layout.addStretch()

    def make_title(self, text, icon_path=None, size=18):
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        if icon_path:
            icon_lbl = QLabel()
            icon = QIcon(icon_path)
            icon_lbl.setPixmap(icon.pixmap(QSize(size + 4, size + 4)))
            icon_lbl.setAlignment(Qt.AlignVCenter)
            layout.addWidget(icon_lbl)

        text_lbl = QLabel(text)
        text_lbl.setStyleSheet(f"font-size:{size}px;font-weight:600;")
        text_lbl.setAlignment(Qt.AlignVCenter)

        layout.addWidget(text_lbl)
        layout.addStretch()

        return wrapper

    def build_branch_section(self):
        box = QFrame()
        box.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(box)

        title = self.make_title(
            t("branch_management"),
            "assets/icons/branch.png",
            size=18
        )
        layout.addWidget(title)


        self.branch_combo = QComboBox()
        self.branch_combo.currentTextChanged.connect(self.change_branch)
        layout.addWidget(self.branch_combo)

        # add branch
        add_row = QHBoxLayout()
        self.new_branch = QLineEdit()
        self.new_branch.setPlaceholderText(t("new_branch_name"))
        add_btn = QPushButton(t("add_branch"))
        add_btn.setIcon(QIcon("assets/icons/add2.png"))
        add_btn.setIconSize(QSize(16, 16))
        add_btn.clicked.connect(self.add_branch_action)
        add_btn.setCursor(QCursor(Qt.PointingHandCursor))

        add_row.addWidget(self.new_branch)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        # rename branch
        edit_row = QHBoxLayout()
        self.rename_branch = QLineEdit()
        self.rename_branch.setPlaceholderText(t("rename_selected_branch"))
        edit_btn = QPushButton(t("update"))
        edit_btn.setIcon(QIcon("assets/icons/edit.png"))
        edit_btn.setIconSize(QSize(16, 16))
        edit_btn.clicked.connect(self.rename_branch_action)
        edit_btn.setCursor(QCursor(Qt.PointingHandCursor))

        edit_row.addWidget(self.rename_branch)
        edit_row.addWidget(edit_btn)
        layout.addLayout(edit_row)

        self.layout.addWidget(box)

    def load_branches(self):
        try:
            self.branches = api_get(
                self.app,
                "/branches/"
            )
        except Exception:
            QMessageBox.critical(self, t("error"), t("cannot_load_branches"))
            return

        self.branch_combo.blockSignals(True)
        self.branch_combo.clear()

        if not self.branches:
            self.branch_combo.addItem(t("no_branches"))
            self.branch_combo.blockSignals(False)
            return

        for b in self.branches:
            self.branch_combo.addItem(f"{b['id']} - {b['name']}")

        config = load_config()
        current_id = config.get("branch_id") or self.branches[0]["id"]

        for i in range(self.branch_combo.count()):
            if self.branch_combo.itemText(i).startswith(f"{current_id} -"):
                self.branch_combo.setCurrentIndex(i)
                break

        self.branch_combo.blockSignals(False)


    
    def change_branch(self, value):
        if not value or "-" not in value:
            return

        branch_id = int(value.split(" - ")[0])

        config = load_config()
        config["branch_id"] = branch_id
        save_config(config)

        self.app.change_branch(branch_id)


        

    def add_branch_action(self):
        name = self.new_branch.text().strip()
        if not name:
            QMessageBox.warning(self, t("error"), t("branch_name_required"))
            return

        try:
            api_post(
                self.app,
                "/branches/",
                {"name": name}
            )
        except Exception:
            QMessageBox.critical(self, t("error"), t("cannot_create_branch"))
            return

        self.new_branch.clear()
        self.load_branches()

        QMessageBox.information(
            self,
            t("success"),
            t("branch_created_select_it")
        )




    def rename_branch_action(self):
        value = self.branch_combo.currentText()
        if not value or "-" not in value:
            return

        branch_id = int(value.split(" - ")[0])
        new_name = self.rename_branch.text().strip()

        if not new_name:
            QMessageBox.warning(self, t("error"), t("branch_name_required"))
            return

        try:
            api_post(
                self.app,
                "/branches/update",
                {
                    "branch_id": branch_id,
                    "name": new_name
                }
            )
        except Exception:
            QMessageBox.critical(self, t("error"), t("cannot_update_branch"))
            return

        self.rename_branch.clear()
        self.load_branches()

        if self.app.current_page and hasattr(self.app.current_page, "refresh"):
            self.app.current_page.refresh()




    def change_password(self):
        old = self.current_password.text().strip()
        new = self.new_password.text().strip()
        confirm = self.confirm_password.text().strip()

        if not old or not new or not confirm:
            QMessageBox.critical(self, t("error"), t("fill_all_fields"))
            return

        if new != confirm:
            QMessageBox.critical(self, t("error"), t("passwords_not_match"))
            return

        api_post(
            self.app,
            "/settings/change-password",
            {
                "current_password": old,
                "new_password": new
            }
        )

        QMessageBox.information(self, t("success"), t("password_changed"))
        self.current_password.clear()
        self.new_password.clear()
        self.confirm_password.clear()

    def switch_lang(self, lang):
        set_lang(lang)
        config = load_config()
        config["language"] = lang
        save_config(config)

        self.app.reload_ui()
