import importlib
import sys

# Legacy bridge for Windows 7/8 builds:
# map PySide6 imports used in the codebase to PySide2 modules.
try:
    import PySide2  # type: ignore
except Exception as exc:
    raise RuntimeError(
        "PySide2 is required for legacy build/runtime. "
        "Install PySide2 in the legacy environment."
    ) from exc

sys.modules.setdefault("PySide6", PySide2)
for mod in ("QtCore", "QtGui", "QtWidgets", "QtCharts"):
    p2_name = f"PySide2.{mod}"
    p6_name = f"PySide6.{mod}"
    try:
        sys.modules.setdefault(p6_name, importlib.import_module(p2_name))
    except Exception:
        # Some deployments may not use all modules (for example QtCharts).
        pass

# PySide2 can expose exec_() in some classes where code calls exec().
try:
    from PySide2 import QtWidgets  # type: ignore

    if hasattr(QtWidgets, "QApplication") and not hasattr(QtWidgets.QApplication, "exec"):
        QtWidgets.QApplication.exec = QtWidgets.QApplication.exec_  # type: ignore[attr-defined]
    if hasattr(QtWidgets, "QDialog") and not hasattr(QtWidgets.QDialog, "exec"):
        QtWidgets.QDialog.exec = QtWidgets.QDialog.exec_  # type: ignore[attr-defined]
except Exception:
    pass

from main_qt import App, load_style, resource_path


def main() -> int:
    # Reuse original app startup from main_qt
    from PySide2.QtGui import QIcon  # type: ignore
    from PySide2.QtWidgets import QApplication  # type: ignore

    app = QApplication(sys.argv)
    icon_path = resource_path("assets/app1.ico")
    app.setWindowIcon(QIcon(icon_path))
    load_style(app)
    win = App()
    win.showMaximized()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
