import requests
from requests import Response
from requests.exceptions import ConnectionError, HTTPError, RequestException, Timeout

from PySide6.QtWidgets import QMessageBox

import i18n

API_URL = "https://hmsuz.com/api"

# One shared session for whole app
SESSION = requests.Session()
TIMEOUT = (10, 30)  # connect, read


class ApiHandledError(Exception):
    """Raised after user-facing API error is already shown."""


def _tr(ru: str, uz: str) -> str:
    return ru if i18n.current_lang == "ru" else uz


def _show_sweet_alert(app, title: str, message: str):
    box = QMessageBox(app)
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle("HMS")
    box.setText(title)
    box.setInformativeText(message)
    box.setStandardButtons(QMessageBox.Ok)
    box.setStyleSheet(
        """
        QMessageBox {
            background: #ffffff;
        }
        QMessageBox QLabel {
            color: #0f172a;
            font-size: 13px;
        }
        QMessageBox QPushButton {
            min-width: 90px;
            padding: 6px 12px;
            border-radius: 10px;
            background: #2563eb;
            color: white;
            border: none;
            font-weight: 600;
        }
        QMessageBox QPushButton:hover {
            background: #1d4ed8;
        }
        """
    )
    box.exec()


def _extract_server_message(response: Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            for key in ("detail", "message", "error"):
                val = data.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
    except Exception:
        pass
    return response.text.strip() or f"HTTP {response.status_code}"


def _handle_unauthorized(app):
    _show_sweet_alert(
        app,
        _tr("Сессия истекла", "Sessiya tugadi"),
        _tr("Пожалуйста, войдите снова.", "Iltimos, qaytadan tizimga kiring."),
    )
    if hasattr(app, "redirect_to_login"):
        app.redirect_to_login()


def _request(app, method: str, path: str, *, params=None, json=None):
    if not getattr(app, "access_token", None):
        _show_sweet_alert(
            app,
            _tr("Требуется вход", "Kirish talab qilinadi"),
            _tr("Пожалуйста, войдите в систему.", "Iltimos, tizimga kiring."),
        )
        if hasattr(app, "redirect_to_login"):
            app.redirect_to_login()
        raise ApiHandledError("not logged in")

    try:
        response = SESSION.request(
            method=method,
            url=f"{API_URL}{path}",
            headers={
                "Authorization": f"Bearer {app.access_token}",
            },
            params=params,
            json=json,
            timeout=TIMEOUT,
        )

        if response.status_code == 401:
            _handle_unauthorized(app)
            raise ApiHandledError("unauthorized")

        response.raise_for_status()
        if response.content:
            return response.json()
        return {}

    except Timeout:
        _show_sweet_alert(
            app,
            _tr("Таймаут соединения", "Ulanish vaqti tugadi"),
            _tr(
                "Сервер долго не отвечает. Проверьте интернет и попробуйте снова.",
                "Server javobi kechikdi. Internetni tekshirib, qayta urinib ko'ring.",
            ),
        )
        raise ApiHandledError("timeout")

    except ConnectionError:
        _show_sweet_alert(
            app,
            _tr("Нет интернета", "Internet yo'q"),
            _tr(
                "Проверьте подключение к интернету и повторите попытку.",
                "Internet ulanishini tekshirib, qayta urinib ko'ring.",
            ),
        )
        raise ApiHandledError("connection")

    except HTTPError:
        msg = _extract_server_message(response)
        _show_sweet_alert(
            app,
            _tr("Ошибка сервера", "Server xatosi"),
            msg,
        )
        raise ApiHandledError("http")

    except RequestException as e:
        _show_sweet_alert(
            app,
            _tr("Ошибка сети", "Tarmoq xatosi"),
            str(e),
        )
        raise ApiHandledError("request")


def api_get(app, path, params=None):
    return _request(app, "GET", path, params=params)


def api_post(app, path, json=None):
    return _request(app, "POST", path, json=json)


def api_delete(app, path, params=None):
    return _request(app, "DELETE", path, params=params)


def api_put(app, path, params=None):
    return _request(app, "PUT", path, params=params)
