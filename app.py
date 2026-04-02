import os
import cv2
import json
import sqlite3
import base64
import threading
from datetime import datetime
from pathlib import Path

import numpy as np
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    send_from_directory,
)
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from ultralytics import YOLO

# ──────────────────────────────────────────────
# APP SETUP
# ──────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "avan_secret_key_change_in_prod")

BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "static" / "logs"
MODEL_PATH = BASE_DIR / "model" / "yolov8n.pt"
DB_PATH = BASE_DIR / "database.db"

LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────
# DATABASE
# ──────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    UNIQUE NOT NULL,
            password TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp  TEXT NOT NULL,
            event_type TEXT NOT NULL,
            objects    TEXT NOT NULL,
            snapshot   TEXT
        );
    """)
    conn.commit()
    conn.close()


init_db()

# ──────────────────────────────────────────────
# YOLO MODEL (lazy-load)
# ──────────────────────────────────────────────
yolo_model = None


def get_model():
    global yolo_model
    if yolo_model is None:
        yolo_model = YOLO(str(MODEL_PATH))
    return yolo_model


# ──────────────────────────────────────────────
# APP STATE
# ──────────────────────────────────────────────
camera_state = {
    "running": False,
    "prev_objects": set(),
    "lock": threading.Lock(),
    "event_count": 0,
}


def save_event(event_type: str, objects: list, frame):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fname = datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".jpg"
    fpath = LOGS_DIR / fname

    try:
        cv2.imwrite(str(fpath), frame)
    except Exception as e:
        print(f"[WARN] Could not save snapshot: {e}")
        fname = None

    conn = get_db()
    conn.execute(
        "INSERT INTO events (timestamp, event_type, objects, snapshot) VALUES (?, ?, ?, ?)",
        (timestamp, event_type, json.dumps(objects), fname),
    )
    conn.commit()
    conn.close()

    camera_state["event_count"] += 1
    print(f"[EVENT] {event_type} | {objects} | {fname}")


# ──────────────────────────────────────────────
# AUTH DECORATOR
# ──────────────────────────────────────────────
def login_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated


# ──────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    login_error = None
    register_success = session.pop("register_success", False)

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))

        login_error = "Incorrect username or password."

    return render_template(
        "login.html",
        login_error=login_error,
        register_success=register_success,
        show_register=False,
    )


@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if len(username) < 3:
        return render_template(
            "login.html",
            register_error="Username must be at least 3 characters.",
            show_register=True,
            reg_username=username,
        )

    if len(password) < 6:
        return render_template(
            "login.html",
            register_error="Password must be at least 6 characters.",
            show_register=True,
            reg_username=username,
        )

    if password != confirm_password:
        return render_template(
            "login.html",
            register_error="Passwords do not match.",
            show_register=True,
            reg_username=username,
        )

    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        conn.commit()
        conn.close()
    except Exception:
        return render_template(
            "login.html",
            register_error="Username already taken. Please choose another.",
            show_register=True,
            reg_username=username,
        )

    session["register_success"] = True
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    events = conn.execute(
        "SELECT * FROM events ORDER BY id DESC LIMIT 50"
    ).fetchall()
    conn.close()

    return render_template(
        "dashboard.html",
        username=session["username"],
        events=events,
        camera_running=camera_state["running"],
    )


# ── Compatibility routes for your dashboard buttons ──
@app.route("/start-camera", methods=["POST"])
@login_required
def start_camera():
    with camera_state["lock"]:
        camera_state["running"] = True
        camera_state["prev_objects"] = set()
    return jsonify({"status": "started"})


@app.route("/stop-camera", methods=["POST"])
@login_required
def stop_camera():
    with camera_state["lock"]:
        camera_state["running"] = False
        camera_state["prev_objects"] = set()
    return jsonify({"status": "stopped"})


# ── CLEAR HISTORY ──
@app.route("/clear-history", methods=["POST"])
@login_required
def clear_history():
    conn = get_db()
    events = conn.execute(
        "SELECT snapshot FROM events WHERE snapshot IS NOT NULL"
    ).fetchall()

    deleted_files = 0
    for row in events:
        if not row["snapshot"]:
            continue
        fpath = LOGS_DIR / row["snapshot"]
        try:
            if fpath.exists():
                fpath.unlink()
                deleted_files += 1
        except Exception as e:
            print(f"[WARN] Could not delete {fpath}: {e}")

    count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    conn.execute("DELETE FROM events")
    conn.commit()
    conn.close()

    with camera_state["lock"]:
        camera_state["event_count"] = 0
        camera_state["prev_objects"] = set()

    print(f"[CLEAR] Deleted {count} events, {deleted_files} snapshot files")
    return jsonify(
        {
            "status": "cleared",
            "deleted": count,
            "files": deleted_files,
        }
    )


# ── API ──
@app.route("/api/status")
@login_required
def api_status():
    with camera_state["lock"]:
        objs = list(camera_state["prev_objects"])
        running = camera_state["running"]
        event_count = camera_state["event_count"]

    return jsonify(
        {
            "running": running,
            "objects": objs,
            "event_count": event_count,
        }
    )


@app.route("/api/events")
@login_required
def api_events():
    conn = get_db()
    events = conn.execute(
        "SELECT * FROM events ORDER BY id DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return jsonify([dict(e) for e in events])


@app.route("/static/logs/<path:filename>")
@login_required
def serve_log(filename):
    return send_from_directory(LOGS_DIR, filename)


@app.route("/detect", methods=["POST"])
@login_required
def detect():
    data = request.get_json(silent=True) or {}
    image_data = data.get("image", "")

    if not image_data:
        return jsonify({"error": "missing image"}), 400

    if "," in image_data:
        image_data = image_data.split(",", 1)[1]

    try:
        img_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({"error": "invalid image"}), 400
    except Exception:
        return jsonify({"error": "could not decode image"}), 400

    model = get_model()
    results = model(frame, verbose=False)[0]

    objects = []
    boxes = getattr(results, "boxes", None)
    if boxes is not None and len(boxes) > 0:
        for cls in boxes.cls.tolist():
            name = results.names[int(cls)]
            if name not in objects:
                objects.append(name)

    with camera_state["lock"]:
        prev_objects = set(camera_state["prev_objects"])
        current_objects = set(objects)
        camera_state["running"] = True
        camera_state["prev_objects"] = current_objects

    appeared = current_objects - prev_objects
    disappeared = prev_objects - current_objects

    if appeared:
        save_event("APPEARED", list(appeared), frame)

    if disappeared:
        save_event("DISAPPEARED", list(disappeared), frame)

    return jsonify(
        {
            "objects": objects,
            "appeared": list(appeared),
            "disappeared": list(disappeared),
            "event_count": camera_state["event_count"],
        }
    )


# ──────────────────────────────────────────────
# RUN
# ──────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000, threaded=True)