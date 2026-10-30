"""Authentication for Prey Open AGI: password and Google OAuth."""
import hmac
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse

from authlib.integrations.flask_client import OAuth
from flask import (
    Blueprint, abort, current_app, flash, g, redirect, render_template_string,
    request, session, url_for
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash, generate_password_hash

bp = Blueprint("auth", __name__, url_prefix="/auth")
oauth = OAuth()
limiter = Limiter(key_func=get_remote_address, default_limits=["300 per hour"])
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
AUTH_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="same-origin"><title>{{ title }} · Prey Open AGI</title><style>
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;padding:22px;background:radial-gradient(circle at 15% 10%,#123747,transparent 38%),#07131d;color:#eaf3fa;font:15px/1.6 Inter,system-ui,sans-serif}.card{width:min(460px,100%);padding:30px;border:1px solid #244151;border-radius:22px;background:#102330;box-shadow:0 24px 80px #0005}.brand{color:#35d7c0;font-weight:850;letter-spacing:.12em;font-size:12px}.card h1{margin:10px 0 4px;font-size:28px}.muted{color:#a6bbc8;font-size:13px;margin:0 0 22px}label{display:block;margin:14px 0 6px;font-weight:650;font-size:13px}input{width:100%;padding:13px;border-radius:11px;border:1px solid #315064;background:#071722;color:#f1f7fa;font:inherit}input:focus{outline:2px solid #35d7c0;border-color:transparent}button,.google{width:100%;display:flex;justify-content:center;align-items:center;margin-top:16px;padding:13px;border:0;border-radius:11px;background:linear-gradient(100deg,#35d7c0,#69aaff);color:#06131b;font-weight:800;text-decoration:none;cursor:pointer}.google{background:#f7fafc;color:#17212b;border:1px solid #dce4e9}.switch{text-align:center;color:#a6bbc8;margin-top:20px;font-size:13px}.switch a,.back{color:#55ddcf}.back{display:inline-block;margin-top:18px;text-decoration:none}.notice{padding:11px 13px;margin:12px 0;border-radius:10px;background:#173b45;color:#c9f7ed;font-size:13px}.error{background:#48252d;color:#ffe0e4}.divider{display:flex;align-items:center;gap:12px;color:#8299a8;font-size:12px;margin:16px 0}.divider:before,.divider:after{content:"";height:1px;background:#315064;flex:1}.founder{display:inline-block;margin-top:10px;padding:4px 9px;border:1px solid #36d7bf;border-radius:99px;color:#55e0cb;font-size:11px;font-weight:800;letter-spacing:.08em}
</style></head><body><main class="card"><div class="brand">PREY OPEN AGI</div><h1>{{ title }}</h1><p class="muted">{{ subtitle }}</p>
{% for category,message in get_flashed_messages(with_categories=true) %}<div class="notice {{ 'error' if category=='error' else '' }}">{{ message }}</div>{% endfor %}
{% if google_enabled %}<a class="google" href="{{ url_for('auth.google_login') }}">Continue with Google</a><div class="divider">OR USE EMAIL</div>{% endif %}
<form method="post" action="{{ form_action }}"><input type="hidden" name="csrf_token" value="{{ csrf_token }}">
{% if register %}<label for="name">Name</label><input id="name" name="name" maxlength="80" autocomplete="name" required>{% endif %}
<label for="email">Email address</label><input id="email" name="email" type="email" maxlength="254" autocomplete="email" required>
<label for="password">Password</label><input id="password" name="password" type="password" minlength="12" maxlength="256" autocomplete="{{ 'new-password' if register else 'current-password' }}" required>
{% if register %}<p class="muted">Use at least 12 characters. Do not reuse a password from another service.</p>{% endif %}
<button type="submit">{{ 'Create account' if register else 'Sign in' }}</button></form>
{% if register %}<p class="switch">Already registered? <a href="{{ url_for('auth.login') }}">Sign in</a></p>{% else %}<p class="switch">New here? <a href="{{ url_for('auth.register') }}">Create an account</a></p>{% endif %}
<a class="back" href="/">← Back to Prey Open AGI</a></main></body></html>"""

def _db_path():
    root = Path(os.getenv("DATA_DIR", str(Path(__file__).resolve().parent / "instance")))
    root.mkdir(parents=True, exist_ok=True)
    return root / "prey_users.sqlite3"

def _connect():
    conn = sqlite3.connect(str(_db_path()), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def _init_db():
    with _connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            name TEXT NOT NULL,
            password_hash TEXT,
            google_sub TEXT UNIQUE,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL
        )""")

def _seed_founder():
    email = os.getenv("FOUNDER_EMAIL", "").strip().lower()
    password = os.getenv("FOUNDER_PASSWORD", "")
    if not email or not EMAIL_RE.fullmatch(email) or len(password) < 12:
        current_app.logger.warning("Founder account not seeded: configure valid FOUNDER_EMAIL and FOUNDER_PASSWORD (12+ chars).")
        return
    with _connect() as db:
        row = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        hashed = generate_password_hash(password, method="scrypt")
        if row:
            db.execute("UPDATE users SET role='founder', password_hash=? WHERE id=?", (hashed, row["id"]))
        else:
            db.execute("INSERT INTO users(email,name,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                       (email, email.split("@")[0], hashed, "founder", datetime.now(timezone.utc).isoformat()))

def _csrf():
    token = session.get("_csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf"] = token
    return token

def _check_csrf():
    supplied = request.form.get("csrf_token", "")
    expected = session.get("_csrf", "")
    if not supplied or not expected or not hmac.compare_digest(supplied, expected):
        abort(400, description="Invalid or expired form token. Refresh and try again.")

def _login_user(user):
    session.clear()
    session["user_id"] = user["id"]
    session["_csrf"] = secrets.token_urlsafe(32)
    session.permanent = True

def _render(title, subtitle, register=False):
    return render_template_string(AUTH_HTML, title=title, subtitle=subtitle,
        register=register, google_enabled=bool(current_app.config.get("GOOGLE_OAUTH_ENABLED")),
        csrf_token=_csrf(), form_action=request.path)

@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per 10 minutes", methods=["POST"])
def login():
    if request.method == "POST":
        _check_csrf()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with _connect() as db:
            user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if not user or not user["password_hash"] or not check_password_hash(user["password_hash"], password):
            flash("Email or password is incorrect.", "error")
            return _render("Welcome back", "Sign in securely to your workspace.")
        _login_user(user)
        return redirect(request.args.get("next") if _safe_next(request.args.get("next")) else url_for("index"))
    return _render("Welcome back", "Sign in securely to your workspace.")

@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def register():
    if request.method == "POST":
        _check_csrf()
        email = request.form.get("email", "").strip().lower()
        name = request.form.get("name", "").strip()[:80]
        password = request.form.get("password", "")
        if not EMAIL_RE.fullmatch(email) or len(email) > 254:
            flash("Enter a valid email address.", "error")
        elif len(password) < 12 or len(password) > 256:
            flash("Password must be between 12 and 256 characters.", "error")
        elif email == os.getenv("FOUNDER_EMAIL", "").strip().lower():
            flash("This email is reserved for the configured founder account. Sign in with the founder password.", "error")
        else:
            try:
                with _connect() as db:
                    db.execute("INSERT INTO users(email,name,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                        (email, name or email.split("@")[0], generate_password_hash(password, method="scrypt"),
                         "user", datetime.now(timezone.utc).isoformat()))
                flash("Account created. You can now sign in.", "success")
                return redirect(url_for("auth.login"))
            except sqlite3.IntegrityError:
                flash("An account with this email already exists. Please sign in.", "error")
    return _render("Create your account", "Join Prey Open AGI with a secure email and password.", True)

@bp.route("/google")
def google_login():
    if not current_app.config.get("GOOGLE_OAUTH_ENABLED"):
        abort(503, description="Google sign-in is not configured.")
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri, prompt="select_account")

@bp.route("/google/callback")
def google_callback():
    if not current_app.config.get("GOOGLE_OAUTH_ENABLED"):
        abort(503)
    try:
        token = oauth.google.authorize_access_token()
        info = oauth.google.userinfo()
    except Exception:
        current_app.logger.exception("Google OAuth callback failed")
        flash("Google sign-in could not be completed. Please try again.", "error")
        return redirect(url_for("auth.login"))
    email = (info.get("email") or "").strip().lower()
    subject = info.get("sub")
    if not email or not subject or not info.get("email_verified"):
        flash("Google did not provide a verified email address.", "error")
        return redirect(url_for("auth.login"))
    founder_email = os.getenv("FOUNDER_EMAIL", "").strip().lower()
    role = "founder" if founder_email and hmac.compare_digest(email, founder_email) else "user"
    with _connect() as db:
        row = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if row:
            db.execute("UPDATE users SET google_sub=?, role=? WHERE id=?", (subject, role, row["id"]))
            user = db.execute("SELECT * FROM users WHERE id=?", (row["id"],)).fetchone()
        else:
            db.execute("INSERT INTO users(email,name,google_sub,role,created_at) VALUES(?,?,?,?,?)",
                (email, (info.get("name") or email.split("@")[0])[:80], subject, role,
                 datetime.now(timezone.utc).isoformat()))
            user = db.execute("SELECT * FROM users WHERE google_sub=?", (subject,)).fetchone()
    _login_user(user)
    return redirect(url_for("index"))

@bp.route("/logout", methods=["POST"])
def logout():
    _check_csrf()
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.login"))

def _safe_next(target):
    if not target:
        return False
    parsed = urlparse(target)
    return not parsed.netloc and target.startswith("/") and not target.startswith("//")

def init_auth(app):
    app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "true").lower() == "true",
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 7,
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        GOOGLE_OAUTH_ENABLED=bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET")),
    )
    app.register_blueprint(bp)
    oauth.init_app(app)
    if app.config["GOOGLE_OAUTH_ENABLED"]:
        oauth.register(name="google", client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"), server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope":"openid email profile"})
    limiter.init_app(app, storage_uri=os.getenv("REDIS_URL", "memory://"))
    _init_db()
    with app.app_context():
        _seed_founder()

    @app.before_request
    def load_and_require_user():
        if request.endpoint and request.endpoint.startswith("static"):
            return None
        if request.endpoint and request.endpoint.startswith("auth."):
            return None
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("auth.login", next=request.full_path if request.query_string else request.path))
        with _connect() as db:
            user = db.execute("SELECT id,email,name,role FROM users WHERE id=?", (user_id,)).fetchone()
        if not user:
            session.clear()
            return redirect(url_for("auth.login"))
        g.current_user = dict(user)
        return None

    @app.context_processor
    def inject_auth_context():
        user = getattr(g, "current_user", None)
        return {"current_user": user, "csrf_token": _csrf}
