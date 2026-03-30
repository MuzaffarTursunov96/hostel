from flask import Flask, render_template, request, jsonify, session, redirect, Response
import requests
from functools import wraps
import os
from dotenv import load_dotenv
from telegram_auth import verify_telegram_init_data
import jwt
from datetime import datetime, timezone
import json



API_URL = "http://backend:8000"
VERSION ="2026-30-03-22-28"
load_dotenv()
ROOT_ADMIN_TELEGRAM = os.getenv("ROOT_ADMIN_TELEGRAM", "muzaffar_developer")
ROOT_ADMIN_PHONE = os.getenv("ROOT_ADMIN_PHONE", "+998991422110")
ROOT_TELEGRAM_ID = int(os.getenv("ROOT_TELEGRAM_ID", "1343842535"))
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
LEADS_FILE = os.getenv("LEADS_FILE", "tmp/hms_sales_leads.jsonl")
MARKETING_CONTENT_FILE = os.getenv("MARKETING_CONTENT_FILE", "content/marketing_content.json")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if not os.path.isabs(MARKETING_CONTENT_FILE):
    MARKETING_CONTENT_FILE = os.path.join(BASE_DIR, MARKETING_CONTENT_FILE)
if not os.path.isabs(LEADS_FILE):
    LEADS_FILE = os.path.join(BASE_DIR, LEADS_FILE)


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
    }





def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "access_token" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper


def is_root_admin_session():
    return bool(session.get("is_admin")) and int(session.get("telegram_id") or 0) == ROOT_TELEGRAM_ID


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
    return render_template("login.html")

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
    # session["branch_id"] = payload["branch_id"]

    with open("/tmp/telegram_payload.log", "a") as f:
        f.write("CALLING BACKEND /api/auth/telegram\n")
        f.write(f"user={payload}\n")

    return jsonify({"ok": True})



@app.post("/login")
def do_login():
    data = request.json

    r = requests.post(
        f"{API_URL}/api/auth/login",
        json={
            "username": data.get("username"),
            "password": data.get("password")
        },
        timeout=(10,20)
    )

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



