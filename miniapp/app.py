from flask import Flask, render_template, request, jsonify, session,redirect,Response
import requests
from functools import wraps
import os
from dotenv import load_dotenv
from telegram_auth import verify_telegram_init_data
import jwt



API_URL = "http://backend:8000"


load_dotenv()


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")



from utils.i18n import TRANSLATIONS  # adjust import

@app.context_processor
def inject_globals():
    lang = session.get("language", "ru")

    def t(key):
        return TRANSLATIONS.get(lang, {}).get(key, key)

    return {
        "t": t,                       # for HTML
        "TRANSLATIONS": TRANSLATIONS, # for JS
        "CURRENT_LANG": lang          # for JS
    }





def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "access_token" not in session:
            return redirect("/")
        return f(*args, **kwargs)
    return wrapper

@app.route("/")
def login_page():   # 🔥 renamed
    return render_template("login.html")

@app.post("/auth/replace-token")
@login_required
def replace_token():
    data = request.get_json()
    token = data["access_token"]

    # 🔥 Decode WITHOUT verifying signature
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

    r = requests.post(
        f"{API_URL}/api/auth/telegram",
        json={
            "telegram_id": user["id"],
            "username": user.get("username")
        },
        timeout=5
    )

    if r.status_code != 200:
        return jsonify({"error": "Backend auth failed"}), 401

    payload = r.json()

    # 🔐 STORE SESSION
    session["access_token"] = payload["access_token"]
    session["user_id"] = payload["user_id"]
    session["is_admin"] = payload["is_admin"]

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
        timeout=5
    )

    if r.status_code == 200:
        payload = r.json()
        session["access_token"] = payload["access_token"]
        session["user_id"] = payload["user_id"]
        session["is_admin"] = payload["is_admin"]
        session["branch_id"] = payload["branch_id"]

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



@app.route("/api/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
@login_required
def api_proxy(path):
    url = f"{API_URL}/api/{path}"

    headers = {
        "Authorization": f"Bearer {session['access_token']}"
    }

    # ✅ CASE 1: multipart/form-data (FILE UPLOAD)
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
            files=files,           # 🔥 IMPORTANT
            data=request.form,     # 🔥 IMPORTANT
            timeout=15
        )

    # ✅ CASE 2: JSON or normal request
    else:
        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            params=request.args,
            json=request.get_json(silent=True),
            timeout=15
        )

    # ✅ response passthrough
    if resp.headers.get("content-type", "").startswith("application/json"):
        return jsonify(resp.json()), resp.status_code

    return resp.content, resp.status_code





@app.route("/dashboard")
@login_required
def dashboard():
    return render_template(
        "dashboard.html"
    )

@app.route("/rooms")
@login_required
def rooms():
    
    return render_template(
        "rooms.html",
        current_branch_id=session.get("branch_id", 1)
        )

@app.route("/bookings")
@login_required
def bookings():
    return render_template(
        "bookings.html",
        current_branch_id=session.get("branch_id", 1)
        )

@app.route("/customers")
@login_required
def customers():
   
    return render_template(
        "customers.html",
        current_branch_id=session.get("branch_id", 1)
        )



@app.route("/payments")
@login_required
def payments_page():
   
    return render_template(
        "payments.html",
        current_branch_id=session.get("branch_id", 1)
    )

@app.route("/payment-history")
@login_required
def payment_history_page():
    return render_template(
        "payment_history.html",
        current_branch_id=session.get("branch_id", 1)
    )

@app.route("/debts")
@login_required
def debts():
    return render_template(
        "debts.html",
        current_branch_id=session.get("branch_id", 1)
    )

@app.route("/settings")
@login_required
def settings():
    return render_template(
        "settings.html",
        current_branch_id=session.get("branch_id", 1)
    )


@app.post("/auth/save-context")
@login_required
def save_context():
    data = request.get_json() or {}

    branch_id = data.get("branch_id", 1)

    session["branch_id"] = int(branch_id)

    return {"ok": True}



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8002)
