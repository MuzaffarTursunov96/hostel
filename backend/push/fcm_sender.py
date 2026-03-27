import os
from typing import Any

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except Exception:  # pragma: no cover - optional runtime dependency
    firebase_admin = None
    credentials = None
    messaging = None


def _credentials_path() -> str | None:
    return (
        os.getenv("FIREBASE_CREDENTIALS_JSON")
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    )


def _ensure_firebase_initialized() -> tuple[bool, str | None]:
    if firebase_admin is None or credentials is None or messaging is None:
        return False, "firebase_admin package is not installed"

    if firebase_admin._apps:  # pylint: disable=protected-access
        return True, None

    cred_path = _credentials_path()
    if not cred_path:
        return False, "Firebase credentials path is not configured"
    if not os.path.exists(cred_path):
        return False, f"Firebase credentials file not found: {cred_path}"

    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        return True, None
    except Exception as exc:  # pragma: no cover - runtime dependent
        return False, str(exc)


def _is_invalid_token_error(err_text: str) -> bool:
    text = (err_text or "").lower()
    return any(
        marker in text
        for marker in (
            "notregistered",
            "registration-token-not-registered",
            "invalid-registration-token",
            "invalid argument",
            "unregistered",
        )
    )


def send_push_to_tokens(
    tokens: list[str],
    title: str,
    body: str,
    data: dict[str, Any] | None = None
) -> dict[str, Any]:
    unique_tokens = []
    seen = set()
    for t in tokens or []:
        token = str(t or "").strip()
        if token and token not in seen:
            seen.add(token)
            unique_tokens.append(token)

    if not unique_tokens:
        return {"sent": 0, "failed": 0, "invalid_tokens": [], "errors": []}

    ok, reason = _ensure_firebase_initialized()
    if not ok:
        return {
            "sent": 0,
            "failed": len(unique_tokens),
            "invalid_tokens": [],
            "errors": [{"token": None, "error": reason}],
            "disabled": True
        }

    result = {"sent": 0, "failed": 0, "invalid_tokens": [], "errors": []}
    payload_data = {str(k): str(v) for k, v in (data or {}).items()}

    for token in unique_tokens:
        try:
            message = messaging.Message(
                token=token,
                notification=messaging.Notification(title=title, body=body),
                data=payload_data
            )
            messaging.send(message)
            result["sent"] += 1
        except Exception as exc:  # pragma: no cover - runtime dependent
            result["failed"] += 1
            err_text = str(exc)
            result["errors"].append({"token": token, "error": err_text})
            if _is_invalid_token_error(err_text):
                result["invalid_tokens"].append(token)

    return result

