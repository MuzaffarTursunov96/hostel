from flask import Flask, render_template, request, jsonify, session, redirect, Response
import requests
from functools import wraps
import os
from dotenv import load_dotenv
from telegram_auth import verify_telegram_init_data
import jwt
from datetime import datetime, timezone, timedelta
import json
import re
import random
import hmac
import smtplib
import secrets
from email.mime.text import MIMEText



API_URL = "http://backend:8000"
VERSION ="2026-31-03-13-18"
load_dotenv()
ROOT_ADMIN_TELEGRAM = os.getenv("ROOT_ADMIN_TELEGRAM", "muzaffar_developer")
ROOT_ADMIN_PHONE = os.getenv("ROOT_ADMIN_PHONE", "+998991422110")
ROOT_TELEGRAM_ID = int(os.getenv("ROOT_TELEGRAM_ID", "1343842535"))
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
LEADS_FILE = os.getenv("LEADS_FILE", "tmp/hms_sales_leads.jsonl")
MARKETING_CONTENT_FILE = os.getenv("MARKETING_CONTENT_FILE", "content/marketing_content.json")
EMAIL_OTP_TTL_SECONDS = int(os.getenv("EMAIL_OTP_TTL_SECONDS", "300"))
EMAIL_OTP_RESEND_SECONDS = int(os.getenv("EMAIL_OTP_RESEND_SECONDS", "60"))
EMAIL_OTP_MAX_ATTEMPTS = int(os.getenv("EMAIL_OTP_MAX_ATTEMPTS", "5"))
EMAIL_VERIFICATION_REQUIRED = str(os.getenv("EMAIL_VERIFICATION_REQUIRED", "1")).strip().lower() not in ("0", "false", "no")
EMAIL_ALLOWED_DOMAINS = {
    d.strip().lower()
    for d in str(os.getenv("EMAIL_ALLOWED_DOMAINS", "gmail.com")).split(",")
    if d.strip()
}
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USERNAME or "noreply@example.com")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")
MINI_APP_URL = os.getenv("MINI_APP_URL", "")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if not os.path.isabs(MARKETING_CONTENT_FILE):
    MARKETING_CONTENT_FILE = os.path.join(BASE_DIR, MARKETING_CONTENT_FILE)
if not os.path.isabs(LEADS_FILE):
    LEADS_FILE = os.path.join(BASE_DIR, LEADS_FILE)

EMAIL_OTP_STORE = {}


app = Flask(__name__,static_folder="static", static_url_path="/static")
app.secret_key = os.getenv("FLASK_SECRET_KEY")




app.config.update(
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_NAME="hostel_session",
)



from utils.i18n import TRANSLATIONS  # adjust import

@app.context_processor
def inject_globals():
    lang = session.get("language", "ru")

    def looks_broken(text):
        if not isinstance(text, str):
            return False
        bad_tokens = ("Рџ", "Р°", "СЃ", "вЂ", "Ð", "Ñ", "�")
        return any(token in text for token in bad_tokens)

    def t(key):
        value = TRANSLATIONS.get(lang, {}).get(key, key)
        if looks_broken(value):
            return TRANSLATIONS.get("uz", {}).get(key, key)
        return value

    return {
        "t": t,                       # for HTML
        "TRANSLATIONS": TRANSLATIONS, # for JS
        "CURRENT_LANG": lang,         # for JS
        "ROOT_ADMIN_TELEGRAM": ROOT_ADMIN_TELEGRAM,
        "ROOT_ADMIN_PHONE": ROOT_ADMIN_PHONE,
        "GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID,
        "GOOGLE_OAUTH_ENABLED": "1" if (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET) else "0",
    }





def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "access_token" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper


def is_logged_in_session():
    return "access_token" in session or bool(session.get("public_user_email"))


def require_login_json():
    if is_logged_in_session():
        return None
    return jsonify({"ok": False, "error": "Login required"}), 401


def is_root_admin_session():
    return bool(session.get("is_admin")) and int(session.get("telegram_id") or 0) == ROOT_TELEGRAM_ID


def _normalize_email(value):
    return str(value or "").strip().lower()


def _is_valid_email(email):
    if not re.fullmatch(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$", email):
        return False
    if not EMAIL_ALLOWED_DOMAINS:
        return True
    domain = email.rsplit("@", 1)[-1]
    return domain in EMAIL_ALLOWED_DOMAINS


def _mask_email(email):
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        hidden_local = "*" * len(local)
    else:
        hidden_local = local[0] + ("*" * max(1, len(local) - 2)) + local[-1]
    return f"{hidden_local}@{domain}"


def _send_otp_email(email, code):
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        return False, "SMTP is not configured"

    body = (
        "Your verification code\n\n"
        f"Code: {code}\n"
        f"Expires in: {EMAIL_OTP_TTL_SECONDS // 60} minutes\n\n"
        "If you did not request this code, you can ignore this email."
    )
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "Hostel login verification code"
    msg["From"] = SMTP_FROM
    msg["To"] = email

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [email], msg.as_string())
        return True, None
    except Exception:
        return False, "Failed to send verification code"


def _post_backend_login(username, password):
    payload = {
        "username": username,
        "password": password,
    }
    urls = (f"{API_URL}/auth/login", f"{API_URL}/api/auth/login")
    last_response = None
    for url in urls:
        try:
            resp = requests.post(url, json=payload, timeout=(10, 20))
        except requests.RequestException:
            continue
        if resp.status_code == 404:
            last_response = resp
            continue
        return resp
    return last_response


def _google_redirect_uri():
    if GOOGLE_REDIRECT_URI:
        return GOOGLE_REDIRECT_URI
    if MINI_APP_URL:
        return MINI_APP_URL.rstrip("/") + "/auth/google/callback"
    return request.url_root.rstrip("/") + "/auth/google/callback"


def _build_google_auth_url(state: str):
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": _google_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
        "state": state,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + requests.compat.urlencode(params)


def notify_new_lead(lead):
    if not BOT_TOKEN:
        return False

    lang = lead.get("lang", "uz")
    if lang == "ru":
        message = (
            "\u041d\u043e\u0432\u0430\u044f \u0437\u0430\u044f\u0432\u043a\u0430 (hmsuz.com)\n\n"
            f"\u0418\u043c\u044f: {lead['manager_name']}\n"
            f"\u0422\u0435\u043b\u0435\u0444\u043e\u043d: {lead['phone']}\n"
            f"\u041e\u0431\u044a\u0435\u043a\u0442: {lead['property_name']}\n"
            f"\u0413\u043e\u0440\u043e\u0434: {lead['city']}\n"
            f"\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e \u043a\u043e\u043c\u043d\u0430\u0442: {lead['rooms'] or '-'}\n"
            f"\u0423\u0434\u043e\u0431\u043d\u043e\u0435 \u0432\u0440\u0435\u043c\u044f: {lead['preferred_time'] or '-'}\n"
            f"\u041a\u043e\u043c\u043c\u0435\u043d\u0442\u0430\u0440\u0438\u0439: {lead['note'] or '-'}"
        )
    else:
        message = (
            "Yangi ariza keldi (hmsuz.com)\n\n"
            f"Ism: {lead['manager_name']}\n"
            f"Telefon: {lead['phone']}\n"
            f"Obyekt: {lead['property_name']}\n"
            f"Shahar: {lead['city']}\n"
            f"Xonalar: {lead['rooms'] or '-'}\n"
            f"Qulay vaqt: {lead['preferred_time'] or '-'}\n"
            f"Izoh: {lead['note'] or '-'}"
        )

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": ROOT_TELEGRAM_ID, "text": message},
            timeout=(5, 15),
        )
        return resp.status_code == 200
    except Exception:
        return False


@app.get("/marketing-content")
def marketing_content():
    try:
        with open(MARKETING_CONTENT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception:
        return jsonify({"pricing": [], "videos": [], "content_cards": []}), 200


@app.get("/root-marketing-content")
@login_required
def root_marketing_content():
    if not is_root_admin_session():
        return jsonify({"ok": False, "error": "Root admin only"}), 403
    try:
        with open(MARKETING_CONTENT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify({"ok": True, "content": data})
    except Exception:
        return jsonify({"ok": True, "content": {"pricing": [], "videos": [], "content_cards": []}})


@app.post("/root-marketing-content")
@login_required
def save_root_marketing_content():
    if not is_root_admin_session():
        return jsonify({"ok": False, "error": "Root admin only"}), 403

    payload = request.get_json(silent=True) or {}
    content = payload.get("content")
    if not isinstance(content, dict):
        return jsonify({"ok": False, "error": "Invalid content format"}), 400

    content.setdefault("pricing", [])
    content.setdefault("videos", [])
    content.setdefault("content_cards", [])

    try:
        os.makedirs(os.path.dirname(MARKETING_CONTENT_FILE), exist_ok=True)
        with open(MARKETING_CONTENT_FILE, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        return jsonify({"ok": True})
    except Exception:
        return jsonify({"ok": False, "error": "Failed to save content"}), 500


@app.get("/root-leads")
@login_required
def root_leads():
    if not is_root_admin_session():
        return jsonify({"ok": False, "error": "Root admin only"}), 403

    leads = []
    try:
        if os.path.exists(LEADS_FILE):
            with open(LEADS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        leads.append(json.loads(line))
                    except Exception:
                        continue
        leads = list(reversed(leads[-200:]))
        return jsonify({"ok": True, "leads": leads})
    except Exception:
        return jsonify({"ok": False, "error": "Failed to read leads"}), 500

@app.route("/")
def marketing_page():
    return render_template("marketing.html")

@app.route("/login")
def login_page():
    if "access_token" in session:
        return redirect("/dashboard")
    if session.get("public_user_email"):
        return redirect("/catalog")
    req_lang = str(request.args.get("lang") or "").strip().lower()
    if req_lang not in ("uz", "ru"):
        req_lang = str(session.get("language") or "ru").strip().lower()
    if req_lang not in ("uz", "ru"):
        req_lang = "ru"
    return render_template("login.html", CURRENT_LANG=req_lang)


@app.get("/auth/google/start")
def google_start():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return redirect("/login?google=not_configured")
    state = secrets.token_urlsafe(24)
    session["google_oauth_state"] = state
    return redirect(_build_google_auth_url(state))


@app.get("/auth/google/callback")
def google_callback():
    if request.args.get("error"):
        return redirect("/login?google=cancelled")

    state = str(request.args.get("state") or "")
    expected_state = str(session.get("google_oauth_state") or "")
    session.pop("google_oauth_state", None)
    if not state or not expected_state or state != expected_state:
        return redirect("/login?google=invalid_state")

    code = str(request.args.get("code") or "").strip()
    if not code:
        return redirect("/login?google=missing_code")

    try:
        token_resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": _google_redirect_uri(),
            },
            timeout=(10, 20),
        )
    except requests.RequestException:
        return redirect("/login?google=token_failed")

    if token_resp.status_code != 200:
        return redirect("/login?google=token_failed")

    token_payload = token_resp.json()
    id_token = token_payload.get("id_token")
    if not id_token:
        return redirect("/login?google=id_token_missing")

    try:
        info_resp = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
            timeout=(10, 20),
        )
    except requests.RequestException:
        return redirect("/login?google=tokeninfo_failed")

    if info_resp.status_code != 200:
        return redirect("/login?google=tokeninfo_failed")

    info = info_resp.json()
    if str(info.get("aud") or "") != GOOGLE_CLIENT_ID:
        return redirect("/login?google=aud_mismatch")

    email = _normalize_email(info.get("email"))
    email_verified = str(info.get("email_verified") or "").lower() == "true"
    if not email or not email_verified:
        return redirect("/login?google=email_not_verified")
    if not _is_valid_email(email):
        return redirect("/login?google=invalid_email_domain")

    now = datetime.now(timezone.utc)
    session["verified_email"] = email
    session["verified_email_at"] = now.isoformat()
    session["google_verified_email"] = email

    q = requests.compat.urlencode({"google": "ok", "email": email})
    return redirect(f"/login?{q}")


@app.get("/logout")
def logout_page():
    session.clear()
    return redirect("/catalog")

@app.route("/catalog")
def public_catalog_page():
    return render_template("catalog.html", version=VERSION)

@app.route("/catalog/booking-history")
def public_booking_history_page():
    if not is_logged_in_session():
        return redirect("/login")
    return render_template("catalog_profile_page.html", version=VERSION, page_key="booking_history")

@app.route("/catalog/feedbacks")
def public_feedbacks_page():
    if not is_logged_in_session():
        return redirect("/login")
    return render_template("catalog_profile_page.html", version=VERSION, page_key="feedbacks")

@app.route("/catalog/my-account")
def public_my_account_page():
    if not is_logged_in_session():
        return redirect("/login")
    return render_template("catalog_profile_page.html", version=VERSION, page_key="my_account")

@app.route("/catalog/settings")
def public_catalog_settings_page():
    if not is_logged_in_session():
        return redirect("/login")
    return render_template("catalog_profile_page.html", version=VERSION, page_key="settings")


@app.get("/auth/session-status")
def auth_session_status():
    is_admin = bool(session.get("access_token"))
    is_public = bool(session.get("public_user_email"))
    display_name = (
        session.get("display_name")
        or session.get("public_user_name")
        or (str(session.get("public_user_email") or "").split("@")[0] if session.get("public_user_email") else "")
    )
    return jsonify({
        "ok": True,
        "logged_in": is_admin or is_public,
        "auth_mode": "admin" if is_admin else ("public" if is_public else "guest"),
        "user_id": session.get("user_id"),
        "is_admin": bool(session.get("is_admin")) if is_admin else False,
        "public_user_email": session.get("public_user_email"),
        "display_name": display_name,
    })


@app.get("/public-api/branches")
def public_api_branches():
    resp = requests.get(
        f"{API_URL}/public/branches",
        params=request.args,
        timeout=(10, 20)
    )
    return jsonify(resp.json()), resp.status_code


@app.get("/public-api/branches/<int:branch_id>/photos")
def public_api_branch_photos(branch_id: int):
    resp = requests.get(
        f"{API_URL}/public/branches/{branch_id}/photos",
        params=request.args,
        timeout=(10, 20)
    )
    return jsonify(resp.json()), resp.status_code


@app.get("/public-api/branches/<int:branch_id>/details")
def public_api_branch_details(branch_id: int):
    resp = requests.get(
        f"{API_URL}/public/branches/{branch_id}/details",
        params=request.args,
        timeout=(10, 20)
    )
    return jsonify(resp.json()), resp.status_code


@app.get("/public-api/branches/<int:branch_id>/ratings")
def public_api_branch_ratings(branch_id: int):
    resp = requests.get(
        f"{API_URL}/public/branches/{branch_id}/ratings",
        params=request.args,
        timeout=(10, 20)
    )
    return jsonify(resp.json()), resp.status_code


@app.post("/public-api/branches/<int:branch_id>/ratings")
def public_api_add_rating(branch_id: int):
    guard = require_login_json()
    if guard:
        return guard
    resp = requests.post(
        f"{API_URL}/public/branches/{branch_id}/ratings",
        json=request.get_json(silent=True) or {},
        timeout=(10, 20)
    )
    return jsonify(resp.json()), resp.status_code


@app.get("/public-api/user-history")
def public_api_user_history():
    guard = require_login_json()
    if guard:
        return guard
    resp = requests.get(
        f"{API_URL}/public/user-history",
        params=request.args,
        timeout=(10, 20)
    )
    return jsonify(resp.json()), resp.status_code


@app.post("/public-api/feedback/room-report")
def public_api_room_report():
    guard = require_login_json()
    if guard:
        return guard
    files = {}
    if "file" in request.files:
        f = request.files["file"]
        files["file"] = (f.filename, f.stream, f.mimetype)

    data = dict(request.form)
    resp = requests.post(
        f"{API_URL}/feedback/public-room-report",
        data=data,
        files=files or None,
        timeout=(10, 30)
    )
    return jsonify(resp.json()), resp.status_code


@app.post("/public-api/booking-request")
def public_api_booking_request():
    guard = require_login_json()
    if guard:
        return guard
    resp = requests.post(
        f"{API_URL}/feedback/public-booking-request",
        json=request.get_json(silent=True) or {},
        timeout=(10, 20)
    )
    return jsonify(resp.json()), resp.status_code

@app.post("/lead")
def capture_lead():
    data = request.get_json(silent=True) or {}
    lang = str(data.get("lang", "uz")).strip().lower()
    if lang not in ("uz", "ru"):
        lang = "uz"

    manager_name = str(data.get("manager_name", data.get("full_name", ""))).strip()
    property_name = str(data.get("property_name", "")).strip()
    city = str(data.get("city", "")).strip()
    phone = str(data.get("phone", data.get("phone_number", ""))).strip()
    rooms = str(data.get("rooms", "")).strip()
    preferred_time = str(data.get("preferred_time", "")).strip()
    note = str(data.get("note", "")).strip()

    required = [manager_name, property_name, city, phone]
    if any(not value for value in required):
        error_text = "\u041d\u0435 \u0432\u0441\u0435 \u043e\u0431\u044f\u0437\u0430\u0442\u0435\u043b\u044c\u043d\u044b\u0435 \u043f\u043e\u043b\u044f \u0437\u0430\u043f\u043e\u043b\u043d\u0435\u043d\u044b" if lang == "ru" else "Majburiy maydonlar toldirilmagan"
        return jsonify({"ok": False, "error": error_text}), 400

    lead = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "manager_name": manager_name[:120],
        "property_name": property_name[:180],
        "city": city[:100],
        "phone": phone[:40],
        "rooms": rooms[:20],
        "preferred_time": preferred_time[:60],
        "note": note[:1000],
        "lang": lang,
        "source": "hmsuz.com",
        "user_agent": request.headers.get("User-Agent", "")[:300],
        "ip": request.headers.get("X-Forwarded-For", request.remote_addr),
    }

    try:
        lead_dir = os.path.dirname(LEADS_FILE)
        if lead_dir:
            os.makedirs(lead_dir, exist_ok=True)
        with open(LEADS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(lead, ensure_ascii=True) + "\n")
    except Exception:
        error_text = "\u0412\u0440\u0435\u043c\u0435\u043d\u043d\u0430\u044f \u043e\u0448\u0438\u0431\u043a\u0430 \u0441\u0435\u0440\u0432\u0435\u0440\u0430" if lang == "ru" else "Serverda vaqtinchalik xatolik"
        return jsonify({"ok": False, "error": error_text}), 500

    notified = notify_new_lead(lead)
    return jsonify({"ok": True, "notified": notified})

@app.post("/auth/replace-token")
@login_required
def replace_token():
    data = request.get_json()
    token = data["access_token"]

    # Decode without verifying signature
    payload = jwt.decode(
        token,
        options={"verify_signature": False}
    )

    session["access_token"] = token
    session["language"] = payload.get("language", "ru")
    session["branch_id"] = payload.get("branch_id")

    return {"ok": True}


@app.post("/auth/telegram")
def telegram_auth():
    init_data = request.json.get("initData")

    user = verify_telegram_init_data(init_data)

    if not user:
        return jsonify({"error": "Invalid Telegram auth"}), 401

    with open("/tmp/telegram_flask.log", "a") as f:
        f.write("CALLING BACKEND /api/auth/telegram\n")
        f.write(f"user={user}\n")

    r = requests.post(
        f"{API_URL}/auth/telegram",
        json={
            "telegram_id": user["id"],
            "username": user.get("username")
        },
        timeout=(10,20)
    )

    if r.status_code != 200:
        try:
            payload = r.json()
        except Exception:
            payload = {}
        detail = payload.get("detail") or payload.get("error") or "Backend auth failed"
        return jsonify({"error": detail}), r.status_code

    payload = r.json()
    token_payload = jwt.decode(
        payload["access_token"],
        options={"verify_signature": False}
    )

    # Store session
    session["access_token"] = payload["access_token"]
    session["user_id"] = payload["user_id"]
    session["is_admin"] = payload["is_admin"]
    session["telegram_id"] = payload.get("telegram_id")
    session["language"] = token_payload.get("language", "ru")
    session["branch_id"] = token_payload.get("branch_id")
    session["display_name"] = user.get("username") or user.get("first_name") or "User"
    # session["branch_id"] = payload["branch_id"]

    with open("/tmp/telegram_payload.log", "a") as f:
        f.write("CALLING BACKEND /api/auth/telegram\n")
        f.write(f"user={payload}\n")

    return jsonify({"ok": True})


@app.post("/auth/email/send-code")
def send_email_code():
    data = request.get_json(silent=True) or {}
    email = _normalize_email(data.get("email"))
    if not _is_valid_email(email):
        return jsonify({"ok": False, "error": "Enter a valid Gmail address"}), 400

    now = datetime.now(timezone.utc)
    existing = EMAIL_OTP_STORE.get(email)
    if existing:
        last_sent_at = existing.get("last_sent_at")
        if isinstance(last_sent_at, datetime):
            wait_seconds = int((last_sent_at + timedelta(seconds=EMAIL_OTP_RESEND_SECONDS) - now).total_seconds())
            if wait_seconds > 0:
                return jsonify({
                    "ok": False,
                    "error": f"Please wait {wait_seconds}s before requesting a new code"
                }), 429

    code = f"{random.SystemRandom().randint(0, 999999):06d}"
    sent_ok, sent_error = _send_otp_email(email, code)
    if not sent_ok:
        return jsonify({"ok": False, "error": sent_error}), 500

    EMAIL_OTP_STORE[email] = {
        "code": code,
        "expires_at": now + timedelta(seconds=EMAIL_OTP_TTL_SECONDS),
        "attempts": 0,
        "verified": False,
        "last_sent_at": now,
    }
    return jsonify({"ok": True, "email_masked": _mask_email(email)})


@app.post("/auth/email/verify-code")
def verify_email_code():
    data = request.get_json(silent=True) or {}
    email = _normalize_email(data.get("email"))
    code = str(data.get("code") or "").strip()

    record = EMAIL_OTP_STORE.get(email)
    if not record:
        return jsonify({"ok": False, "error": "Verification code is missing. Request a new code."}), 400

    now = datetime.now(timezone.utc)
    expires_at = record.get("expires_at")
    if not isinstance(expires_at, datetime) or now > expires_at:
        EMAIL_OTP_STORE.pop(email, None)
        return jsonify({"ok": False, "error": "Code expired. Request a new one."}), 400

    record["attempts"] = int(record.get("attempts", 0)) + 1
    if record["attempts"] > EMAIL_OTP_MAX_ATTEMPTS:
        EMAIL_OTP_STORE.pop(email, None)
        return jsonify({"ok": False, "error": "Too many attempts. Request a new code."}), 429

    if not hmac.compare_digest(str(record.get("code", "")), code):
        return jsonify({"ok": False, "error": "Invalid verification code"}), 400

    record["verified"] = True
    session["verified_email"] = email
    session["verified_email_at"] = now.isoformat()
    return jsonify({"ok": True, "email": email})


@app.post("/auth/email/account-status")
def email_account_status():
    data = request.get_json(silent=True) or {}
    email = _normalize_email(data.get("email"))
    verified_email = _normalize_email(session.get("verified_email"))
    if not email or email != verified_email:
        return jsonify({"ok": False, "error": "Verify this email first"}), 403

    r = requests.post(
        f"{API_URL}/auth/email/status",
        json={"email": email},
        timeout=(10, 20)
    )
    payload = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if r.status_code != 200:
        return jsonify({"ok": False, "error": payload.get("detail") or "status check failed"}), r.status_code
    return jsonify({"ok": True, "exists": bool(payload.get("exists"))})


@app.post("/auth/email/account-register")
def email_account_register():
    data = request.get_json(silent=True) or {}
    email = _normalize_email(data.get("email"))
    password = str(data.get("password") or "")
    verified_email = _normalize_email(session.get("verified_email"))
    if not email or email != verified_email:
        return jsonify({"ok": False, "error": "Verify this email first"}), 403

    r = requests.post(
        f"{API_URL}/auth/email/register",
        json={"email": email, "password": password},
        timeout=(10, 20)
    )
    payload = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if r.status_code != 200:
        return jsonify({"ok": False, "error": payload.get("detail") or "register failed"}), r.status_code

    session["public_user_email"] = email
    session["public_user_name"] = payload.get("name") or email.split("@")[0]
    session["display_name"] = session["public_user_name"]
    return jsonify({"ok": True})


@app.post("/auth/email/account-login")
def email_account_login():
    data = request.get_json(silent=True) or {}
    email = _normalize_email(data.get("email"))
    password = str(data.get("password") or "")
    verified_email = _normalize_email(session.get("verified_email"))
    if not email or email != verified_email:
        return jsonify({"ok": False, "error": "Verify this email first"}), 403

    r = requests.post(
        f"{API_URL}/auth/email/login",
        json={"email": email, "password": password},
        timeout=(10, 20)
    )
    payload = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if r.status_code != 200:
        return jsonify({"ok": False, "error": payload.get("detail") or "login failed"}), r.status_code

    session["public_user_email"] = email
    session["public_user_name"] = payload.get("name") or email.split("@")[0]
    session["display_name"] = session["public_user_name"]
    return jsonify({"ok": True})


@app.post("/login")
def do_login():
    data = request.get_json(silent=True) or {}
    if EMAIL_VERIFICATION_REQUIRED and not session.get("verified_email"):
        return jsonify({"ok": False, "error": "Verify your Gmail first"}), 403

    r = _post_backend_login(data.get("username"), data.get("password"))
    if r is None:
        return jsonify({"ok": False, "error": "Authentication service is unavailable"}), 503

    if r.status_code == 200:
        payload = r.json()
        token_payload = jwt.decode(
            payload["access_token"],
            options={"verify_signature": False}
        )
        session["access_token"] = payload["access_token"]
        session["user_id"] = payload["user_id"]
        session["is_admin"] = payload["is_admin"]
        session["telegram_id"] = payload.get("telegram_id")
        session["branch_id"] = token_payload.get("branch_id", payload.get("branch_id"))
        session["language"] = token_payload.get("language", payload.get("language", "ru"))
        session["display_name"] = str(data.get("username") or "User")
        session.pop("verified_email", None)
        session.pop("verified_email_at", None)
        session.pop("public_user_email", None)
        session.pop("public_user_name", None)

    return jsonify(r.json()), r.status_code



@app.route("/static/<path:filename>")
def proxy_static(filename):
    resp = requests.get(
        f"{API_URL}/api/static/{filename}",
        stream=True
    )
    return Response(
        resp.content,
        status=resp.status_code,
        content_type=resp.headers.get("content-type")
    )


@app.get("/api2/__ping")
def api2_ping():
    return {"pong": True}



@app.route("/api2/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
@login_required
def api_proxy(path):
    with open("/tmp/api_proxy.log", "a") as f:
        f.write(f"HIT api_proxy: {path}\n")
    url = f"{API_URL}/{path}"

    headers = {
        "Authorization": f"Bearer {session['access_token']}"
    }

    # Case 1: multipart/form-data (file upload)
    if request.files:
        files = []
        for name, f in request.files.items():
            files.append(
                (name, (f.filename, f.stream, f.mimetype))
            )

        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            params=request.args,
            files=files,           # important
            data=request.form,     # important
            timeout=15
        )

    # Case 2: JSON or normal request
    else:
        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            params=request.args,
            json=request.get_json(silent=True),
            timeout=15
        )

    # Response passthrough
    if resp.headers.get("content-type", "").startswith("application/json"):
        return jsonify(resp.json()), resp.status_code

    return resp.content, resp.status_code





@app.route("/dashboard")
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        version = VERSION
    )

@app.route("/rooms")
@login_required
def rooms():
    
    return render_template(
        "rooms.html",
        # current_branch_id=session.get("branch_id", 1),
        version = VERSION
        )

@app.route("/bookings")
@login_required
def bookings():
    return render_template(
        "bookings.html",
        # current_branch_id=session.get("branch_id", 1),
        version = VERSION
        )

@app.route("/customers")
@login_required
def customers():
   
    return render_template(
        "customers.html",
        # current_branch_id=session.get("branch_id", 1),
        version = VERSION
        )



@app.route("/payments")
@login_required
def payments_page():
    return render_template(
        "payments.html",
        # current_branch_id=session.get("branch_id", 1),
        version = VERSION
    )

@app.route("/payment-history")
@login_required
def payment_history_page():
    return render_template(
        "payment_history.html",
        # current_branch_id=session.get("branch_id", 1),
        version = VERSION
    )

@app.route("/debts")
@login_required
def debts():
    return render_template(
        "debts.html",
        # current_branch_id=session.get("branch_id", 1),
        version = VERSION
    )

@app.route("/settings")
@login_required
def settings():
    return render_template(
        "settings.html",
        current_branch_id=session.get("branch_id", 1),
        version = VERSION
    )

@app.route("/admin-reports")
@login_required
def admin_reports():
    if not bool(session.get("is_admin")):
        return redirect("/dashboard")
    return render_template("admin_reports.html", version=VERSION)

@app.route("/admin-feedback")
@login_required
def admin_feedback():
    if not bool(session.get("is_admin")):
        return redirect("/dashboard")
    return render_template("admin_feedback.html", version=VERSION)


@app.route("/root-management")
@login_required
def root_management():
    if not is_root_admin_session():
        return redirect("/settings")
    return render_template("root_management.html", version=VERSION)


@app.post("/auth/save-context")
@login_required
def save_context():
    data = request.get_json() or {}

    branch_id = data.get("branch_id", 1)

    session["branch_id"] = int(branch_id)

    return {"ok": True}



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8002)



