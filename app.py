import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    send_from_directory, abort
)
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
INSTANCE_DIR = BASE_DIR / "instance"
DB_PATH = INSTANCE_DIR / "submissions.sqlite3"

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "heic", "heif"}

# ---- Flask app ----
app = Flask(__name__, instance_path=str(INSTANCE_DIR))
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev")
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32MB per request
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "changeme")

# Ensure folders exist
UPLOAD_DIR.mkdir(exist_ok=True)
INSTANCE_DIR.mkdir(exist_ok=True)

# ---- DB helpers ----
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            email TEXT NOT NULL,
            apartment TEXT NOT NULL,
            date_iso TEXT NOT NULL,
            person_name TEXT NOT NULL,
            lat REAL,
            lng REAL,
            data_json TEXT NOT NULL,      -- all checkbox states etc.
            files_json TEXT NOT NULL      -- mapping field -> stored filename(s)
        )
        """
    )
    conn.commit()
    conn.close()

init_db()

# ---- Form model (sections) ----
# We’ll render the checklist dynamically so you can tweak labels in one place.
# Each item has a machine-friendly key used in form names + storage.
CHECKLIST = {
    "rooms": [
        {"key": "room1", "title": "🛏️  Chambre 1 || Кімната 1"},
        {"key": "room2", "title": "🛏️  Chambre 2 || Кімната 2"},
        {"key": "room3", "title": "🛏️  Chambre 3 || Кімната 3"},
        {"key": "room4", "title": "🛏️  Chambre 4 || Кімната 4"},
    ],
    "room_tasks": [
        {"key": "bed_made", "label": "Lit fait || Ліжко заправлене"},
        {"key": "floor_clean", "label": "Sol aspiré/lavé || Підлога пропилосошена / вимита"},
        {"key": "dust_removed", "label": "Poussière enlevée || Пил витертий"},
        {"key": "bin_emptied", "label": "Poubelle vidée || Смітник спорожнений"},
    ],
    "kitchen": {
        "key": "kitchen",
        "title": "🍽️ Cuisine || Кухня",
        "required": True,
        "tasks": [
            {"key": "counter_clean", "label": "Plan de travail nettoyé || Робоча поверхня очищена"},
            {"key": "floor_mopped", "label": "Sol lavé || Підлога вимита"},
            {"key": "fridge_outside_clean", "label": "Frigo propre à l’extérieur || Холодильник чистий зовні"},
            {"key": "cupboards_tidy", "label": "Placards rangés || Шафи впорядковані"},
        ],
    },
    "dishes": {
        "key": "dishes",
        "title": "Vaisselle || Посуд",
        "required": True,
        "tasks": [
            {"key": "clean_and_stowed", "label": "Vaisselle propre et rangée (couverts, poêles, casseroles) || Посуд чистий і складений"},
            {"key": "dishwasher_emptied", "label": "Vider le lave-vaisselle || Спорожнити посудомийну машину"},
        ],
    },
    "oven": {
        "key": "oven",
        "title": "Four || Духовка",
        "required": True,
        "tasks": [
            {"key": "inside_clean", "label": "Intérieur propre || Внутрішня частина чиста"},
            {"key": "outside_clean", "label": "Extérieur nettoyé || Зовнішня частина очищена"},
        ],
    },
    "microwave": {
        "key": "microwave",
        "title": "Micro-ondes || Мікрохвильова піч",
        "required": True,
        "tasks": [
            {"key": "mw_inside_clean", "label": "Intérieur propre || Внутрішня частина чиста"},
            {"key": "mw_outside_clean", "label": "Extérieur nettoyé || Зовнішня частина очищена"},
        ],
    },
    "shower": {
        "key": "shower",
        "title": "Douche || Душ",
        "required": True,
        "tasks": [
            {"key": "walls_floor_clean", "label": "Murs et sol nettoyés || Стіни та підлога очищені"},
            {"key": "no_hair_soap", "label": "Pas de cheveux / savon || Немає волосся / мила"},
            {"key": "use_destop_if_clogged", "label": "Mettre du Destop si bouché (à vérifier) || Використати засіб «Destop», якщо забито"},
            {"key": "refill_gel_shampoo", "label": "Remplir gel douche et shampoing || Поповнити запаси гелю для душу та шампуню"},
        ],
    },
    "toilet": {
        "key": "toilet",
        "title": "Toilette || Туалет",
        "required": True,
        "tasks": [
            {"key": "bowl_cleaned", "label": "Cuvette nettoyée || Унітаз очищений"},
            {"key": "toilet_floor_mopped", "label": "Sol lavé || Підлога вимита"},
            {"key": "toilet_paper_present", "label": "Papier toilette présent || Туалетний папір наявний"},
        ],
    },
    "special": {
        "key": "special",
        "title": "📎 Cas spécial ou oubli || Особливий випадок або забуто",
    },
    "extra_photo_comment": {
        "key": "extra",
        "title": "📸 Veuillez ajouter une photo ou un commentaire || Будь ласка, додайте фото або коментар",
    },
}

BEFORE_FILE = "photo_before"
AFTER_FILE = "photo_after"

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ---- Routes ----
@app.route("/")
def index():
    return render_template("form.html", checklist=CHECKLIST)

@app.post("/submit")
def submit():
    # Required top-level fields
    email = request.form.get("email", "").strip()
    apartment = request.form.get("apartment", "").strip()
    date_iso = request.form.get("date", "").strip()
    person_name = request.form.get("person_name", "").strip()
    lat = request.form.get("lat", "").strip() or None
    lng = request.form.get("lng", "").strip() or None

    # Basic validation on required fields
    missing = []
    if not email: missing.append("Email")
    if not apartment: missing.append("Appartement")
    if not date_iso: missing.append("Date")
    if not person_name: missing.append("Nom")

    # Validate required sections: kitchen/dishes/oven/microwave/shower/toilet
    required_sections = [
        CHECKLIST["kitchen"]["key"],
        CHECKLIST["dishes"]["key"],
        CHECKLIST["oven"]["key"],
        CHECKLIST["microwave"]["key"],
        CHECKLIST["shower"]["key"],
        CHECKLIST["toilet"]["key"],
    ]
    section_errors = []

    # Collect checkbox states + file info
    data = {}
    files_map = {}

    # Rooms
    for room in CHECKLIST["rooms"]:
        rkey = room["key"]
        room_block = {}
        # tasks
        for task in CHECKLIST["room_tasks"]:
            tkey = f"{rkey}__{task['key']}"
            room_block[task["key"]] = request.form.get(tkey) == "on"
        # files
        before_field = f"{rkey}__{BEFORE_FILE}"
        after_field = f"{rkey}__{AFTER_FILE}"
        files_map.setdefault(rkey, {})
        files_map[rkey][BEFORE_FILE] = None
        files_map[rkey][AFTER_FILE] = None

        for fname, label in [(before_field, BEFORE_FILE), (after_field, AFTER_FILE)]:
            f = request.files.get(fname)
            if f and f.filename and allowed_file(f.filename):
                cleaned = secure_filename(f.filename)
                # We'll save into a temp holder after we get submission ID.
                files_map[rkey][label] = cleaned
        data[rkey] = room_block

    # Other sections
    def handle_section(section):
        skey = section["key"]
        block = {}
        for task in section["tasks"]:
            tkey = f"{skey}__{task['key']}"
            block[task["key"]] = request.form.get(tkey) == "on"
        # required check: at least one box ticked?
        if section.get("required") and not any(block.values()):
            section_errors.append(section["title"])
        # files
        before_field = f"{skey}__{BEFORE_FILE}"
        after_field = f"{skey}__{AFTER_FILE}"
        files_map.setdefault(skey, {})
        files_map[skey][BEFORE_FILE] = None
        files_map[skey][AFTER_FILE] = None
        for fname, label in [(before_field, BEFORE_FILE), (after_field, AFTER_FILE)]:
            f = request.files.get(fname)
            if f and f.filename and allowed_file(f.filename):
                cleaned = secure_filename(f.filename)
                files_map[skey][label] = cleaned
        data[skey] = block

    handle_section(CHECKLIST["kitchen"])
    handle_section(CHECKLIST["dishes"])
    handle_section(CHECKLIST["oven"])
    handle_section(CHECKLIST["microwave"])
    handle_section(CHECKLIST["shower"])
    handle_section(CHECKLIST["toilet"])

    # Special & extra comments/images (optional)
    data[CHECKLIST["special"]["key"]] = request.form.get("special_text", "").strip()
    files_map.setdefault(CHECKLIST["extra_photo_comment"]["key"], {})
    extra_before = request.files.get("extra__photo")
    if extra_before and extra_before.filename and allowed_file(extra_before.filename):
        files_map[CHECKLIST["extra_photo_comment"]["key"]]["photo"] = secure_filename(extra_before.filename)
    else:
        files_map[CHECKLIST["extra_photo_comment"]["key"]]["photo"] = None
    data[CHECKLIST["extra_photo_comment"]["key"]] = request.form.get("extra_text", "").strip()

    # Combine errors
    if missing or section_errors:
        msg = []
        if missing:
            msg.append("Champs requis manquants / Обов'язкові поля відсутні: " + ", ".join(missing))
        if section_errors:
            msg.append("Sélectionnez au moins une case dans: " + "; ".join(section_errors))
        flash(" | ".join(msg), "danger")
        return redirect(url_for("index"))

    # Insert DB row to get submission ID
    conn = get_db()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute(
        """
        INSERT INTO submissions (created_at, email, apartment, date_iso, person_name, lat, lng, data_json, files_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            now, email, apartment, date_iso, person_name,
            float(lat) if lat else None, float(lng) if lng else None,
            json.dumps(data, ensure_ascii=False),
            json.dumps(files_map, ensure_ascii=False),
        ),
    )
    sub_id = cur.lastrowid
    conn.commit()

    # Save files to /uploads/<sub_id>/
    save_dir = UPLOAD_DIR / str(sub_id)
    save_dir.mkdir(parents=True, exist_ok=True)

    def save_upload(form_field_name, desired_name):
        f = request.files.get(form_field_name)
        if f and f.filename and allowed_file(f.filename):
            # Prefix with field to avoid collisions, but preserve cleaned filename
            path = save_dir / f"{form_field_name}__{desired_name}"
            f.save(path)
            return str(path.name)
        return None

    # Persist and rewrite files_map to actual saved filenames
    saved_files_map = {}
    for section_key, section_files in files_map.items():
        saved_files_map.setdefault(section_key, {})
        if isinstance(section_files, dict):
            for label, fname in section_files.items():
                fieldname = f"{section_key}__{label}"
                if fname:
                    saved_name = save_upload(fieldname, fname)
                else:
                    saved_name = None
                saved_files_map[section_key][label] = saved_name

    # Extra photo key name differs
    if "photo" in files_map.get(CHECKLIST["extra_photo_comment"]["key"], {}):
        ef = save_upload("extra__photo", files_map[CHECKLIST["extra_photo_comment"]["key"]]["photo"] or "extra")
        saved_files_map[CHECKLIST["extra_photo_comment"]["key"]]["photo"] = ef

    # Update DB with actual saved names
    conn.execute(
        "UPDATE submissions SET files_json = ? WHERE id = ?",
        (json.dumps(saved_files_map, ensure_ascii=False), sub_id),
    )
    conn.commit()
    conn.close()

    flash("Merci ! Запис збережено. ✅", "success")
    return redirect(url_for("thank_you", sid=sub_id))

@app.get("/thank-you")
def thank_you():
    sid = request.args.get("sid")
    return render_template("submissions.html", single_id=sid, entries=[])

@app.get("/uploads/<int:sid>/<path:filename>")
def uploaded_file(sid, filename):
    directory = UPLOAD_DIR / str(sid)
    if not directory.exists():
        abort(404)
    return send_from_directory(directory, filename)

@app.get("/admin")
def admin():
    token = request.args.get("token", "")
    if token != ADMIN_TOKEN:
        abort(403)
    # list latest 100
    conn = get_db()
    rows = conn.execute("SELECT * FROM submissions ORDER BY id DESC LIMIT 100").fetchall()
    conn.close()

    entries = []
    for r in rows:
        entries.append({
            "id": r["id"],
            "created_at": r["created_at"],
            "email": r["email"],
            "apartment": r["apartment"],
            "date_iso": r["date_iso"],
            "person_name": r["person_name"],
            "lat": r["lat"],
            "lng": r["lng"],
            "data": json.loads(r["data_json"]),
            "files": json.loads(r["files_json"]),
        })
    return render_template("submissions.html", entries=entries, single_id=None)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
