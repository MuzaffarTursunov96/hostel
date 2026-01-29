from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel,
    QLineEdit, QPushButton
)
from PySide6.QtCore import Qt
# import requests
from .api_session import SESSION, API_URL

from .utils import get_device_id, save_license

API_URL = "https://hmsuz.com/api"


class LicenseDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Activate License")
        self.setFixedSize(360, 200)

        layout = QVBoxLayout(self)

        title = QLabel("License Activation")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:18px;font-weight:700;")

        self.input = QLineEdit()
        self.input.setPlaceholderText("Enter license key")

        self.msg = QLabel("")
        self.msg.setAlignment(Qt.AlignCenter)
        self.msg.setStyleSheet("color:#DC2626;font-size:11px;")

        btn = QPushButton("Activate")
        btn.clicked.connect(self.activate)

        layout.addWidget(title)
        layout.addWidget(self.input)
        layout.addWidget(btn)
        layout.addWidget(self.msg)

    def activate(self):
        key = self.input.text().strip()
        if not key:
            self.msg.setText("License key required")
            return

        try:
            r = SESSION.post(
                f"{API_URL}/license/verify",
                params={
                    "license_key": key,
                    "device_id": get_device_id()
                },
                timeout=(10, 20)
            )

            if r.status_code != 200:
                self.msg.setText(r.text)
                return

            save_license(key)
            self.accept()

        except Exception as e:
            self.msg.setText(str(e))
