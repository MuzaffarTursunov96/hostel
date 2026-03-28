from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QFrame
from PySide6.QtCore import Qt


class BrandWidget(QWidget):
    def __init__(self):
        super().__init__()

        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(0, 6, 0, 10)
        root.setAlignment(Qt.AlignCenter)

        # ===== ICON (DOTS) =====
        dots = QHBoxLayout()
        dots.setSpacing(8)
        dots.setAlignment(Qt.AlignCenter)

        def dot(color):
            d = QFrame()
            d.setFixedSize(14, 10)   # 👈 pill shape
            d.setStyleSheet(f"""
                background-color: {color};
                border-radius: 5px;
            """)
            return d

        dots.addWidget(dot("#2563EB"))  # primary blue
        dots.addWidget(dot("#F59E0B"))  # accent amber
        dots.addWidget(dot("#10B981"))  # success green

        root.addLayout(dots)

        # ===== TITLE =====
        title = QLabel("HMS")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 22px;
            font-weight: 800;
            letter-spacing: 2px;
            color: #0F172A;
        """)

        # ===== SUBTITLE =====
        subtitle = QLabel("HMS")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            font-size: 11px;
            color: #64748B;
        """)

        root.addWidget(title)
        root.addWidget(subtitle)
