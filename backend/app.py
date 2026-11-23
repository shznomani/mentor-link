"""
Mentor Link backend: Flask + SQLite.

THE PRIVACY RULE (enforced here, on the server, not in the HTML):
  No email is ever sent to anyone until a mentor ACCEPTS a request.
  After acceptance, only the two people in that request (the junior who asked
  and the mentor who accepted) can see both emails. Everyone else gets nothing.

How to read this file (top to bottom):
  1. Config + database helpers
  2. Seed (demo) data
  3. Login / tokens
  4. request_view()  <-- the ONE place where contact details can leave the server
  5. API routes
"""
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, current_app, g, jsonify, request, send_from_directory
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash, safe_join

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend", "dist"))

DEMO_PASSWORD = "demo1234"          # password of every seeded demo account
MAX_PENDING_PER_JUNIOR = 5          # stops one student from spamming seniors
BUSY_TEXT = "At capacity this week"
OPEN_TEXT = "Open to requests"


# --------------------------------------------------------------------------
# 1. Config + database helpers
# --------------------------------------------------------------------------
def create_app(config=None):
    app = Flask(__name__, static_folder=None)
    app.config.update(
        DB_PATH=os.environ.get("DB_PATH", os.path.join(BASE_DIR, "mentorlink.db")),
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        # DEMO_MODE=1 turns on /api/demo-login and /api/demo/reset (for the demo video).
        DEMO_MODE=os.environ.get("DEMO_MODE", "1") == "1",
        # Only emails from this domain may register. Set it to your real college domain.
        ALLOWED_DOMAIN=os.environ.get("ALLOWED_DOMAIN", "nie.ac.in").strip().lower(),
        TOKEN_MAX_AGE=60 * 60 * 24,
    )
    if config:
        app.config.update(config)

    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
    register_routes(app)
    return app


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DB_PATH"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    role          TEXT NOT NULL CHECK (role IN ('junior', 'mentor')),
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,      -- PRIVATE: only read inside contact_for() / login
    password_hash TEXT NOT NULL,             -- PRIVATE
    year          TEXT,
    branch        TEXT,
    initials      TEXT,
    avatar        TEXT,
    topics        TEXT NOT NULL DEFAULT '[]',  -- JSON list
    about         TEXT,
    cgpa          TEXT,                        -- optional, mentor chooses to share
    availability  TEXT,
    sessions      INTEGER NOT NULL DEFAULT 0,
    featured      INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS requests (
    id         INTEGER PRIMARY KEY,
    junior_id  INTEGER NOT NULL REFERENCES users(id),
    mentor_id  INTEGER NOT NULL REFERENCES users(id),
    topic      TEXT NOT NULL,
    message    TEXT NOT NULL DEFAULT '',
    tried      TEXT NOT NULL DEFAULT '',
    status     TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined')),
    created_at TEXT NOT NULL,
    decided_at TEXT
);
"""


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        seed_db(db)


# --------------------------------------------------------------------------
# 2. Seed (demo) data. Names and emails are fake. Emails use the reserved
#    ".test" domain, so they can never belong to a real person.
# --------------------------------------------------------------------------
_demo_hash = None


def demo_hash():
    global _demo_hash
    if _demo_hash is None:  # hashing is slow on purpose, so do it once
        _demo_hash = generate_password_hash(DEMO_PASSWORD)
    return _demo_hash


MENTORS = [
    (1, "Ananya Rao", "AR", "4th year", "CSE", "coral", ["Internships", "Frontend", "React", "Resume review"],
     "Frontend engineer intern @ Razorpay. Happy to help you land your first opportunity and build a portfolio that feels like you.",
     "8.8 demo", "Open to requests", 18, 1),
    (2, "Rohan Kulkarni", "RK", "4th year", "ISE", "blue", ["Hackathons", "Product design", "Startups"],
     "Two-time hackathon finalist who loves turning a rough idea into a demo people remember.",
     "8.5 demo", "Limited slots this week", 12, 0),
    (3, "Meera Shetty", "MS", "3rd year", "CSE", "lilac", ["Electives", "Machine learning", "Research"],
     "Research assistant exploring applied ML. Let’s map your interests to electives and a project you’ll be proud of.",
     None, "Open to requests", 9, 0),
    (4, "Aditya Hegde", "AH", "4th year", "ECE", "mint", ["Internships", "Interview prep", "DSA"],
     "Software intern @ Cisco. I can help with interview practice, DSA plans, and figuring out where to begin.",
     "8.2 demo", "Open to requests", 21, 0),
    (5, "Nisha Pai", "NP", "3rd year", "ISE", "peach", ["UI/UX", "Portfolio", "Hackathons"],
     "Designer and builder. I’m happy to review a project, talk through a design portfolio, or brainstorm your next hack.",
     None, "Taking a few requests", 7, 0),
    (6, "Karthik M", "KM", "4th year", "CSE", "slate", ["Open source", "Git & GitHub", "Internships"],
     "Open-source contributor who enjoys making the first PR feel a lot less intimidating.",
     "8.6 demo", BUSY_TEXT, 15, 0),
]

JUNIORS = [
    (7, "Demo Junior", "DJ", "1st year", "CSE", "junior.demo@demo.mentorlink.test"),
    (8, "Demo Junior B", "JB", "1st year", "ISE", "junior.b@demo.mentorlink.test"),
    (9, "Demo Junior C", "JC", "2nd year", "ECE", "junior.c@demo.mentorlink.test"),
]


def seed_db(db):
    """Wipe everything and insert the demo data. Also used by /api/demo/reset."""
    db.execute("DELETE FROM requests")
    db.execute("DELETE FROM users")
    for (uid, name, initials, year, branch, avatar, topics, about, cgpa, availability, sessions, featured) in MENTORS:
        email = name.lower().replace(" ", ".") + "@demo.mentorlink.test"
        db.execute(
            "INSERT INTO users (id, role, name, email, password_hash, year, branch, initials, avatar, topics,"
            " about, cgpa, availability, sessions, featured) VALUES (?, 'mentor', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, name, email, demo_hash(), year, branch, initials, avatar, json.dumps(topics),
             about, cgpa, availability, sessions, featured),
        )
    for (uid, name, initials, year, branch, email) in JUNIORS:
        db.execute(
            "INSERT INTO users (id, role, name, email, password_hash, year, branch, initials, avatar)"
            " VALUES (?, 'junior', ?, ?, ?, ?, ?, ?, 'slate')",
            (uid, name, email, demo_hash(), year, branch, initials),
        )
    # One sample pending request, so the mentor inbox is not empty in the demo.
    db.execute(
        "INSERT INTO requests (junior_id, mentor_id, topic, message, tried, status, created_at)"
        " VALUES (8, 1, 'Internships', 'I want to start applying for internships but I do not know where to begin.',"
        " 'Read a few blog posts, nothing structured yet.', 'pending', ?)",
        (now(),),
    )
    db.commit()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------
# 3. Login / tokens. A token is a signed note saying "this is user #N".
#    The server checks the signature on every request, so it knows WHO is asking.
# --------------------------------------------------------------------------
def serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="mentor-link-auth")


def make_token(user_id):
    return serializer().dumps({"uid": user_id})


def user_from_request():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    try:
        data = serializer().loads(header[7:], max_age=current_app.config["TOKEN_MAX_AGE"])
    except (BadSignature, SignatureExpired):
        return None
    row = get_db().execute(
        "SELECT id, role, name, year, branch FROM users WHERE id = ?", (data.get("uid"),)
    ).fetchone()
    return dict(row) if row else None


def login_required(role=None):
    def wrap(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            user = user_from_request()
            if user is None:
                return jsonify(error="Please sign in first."), 401
            if role and user["role"] != role:
                return jsonify(error=f"Only {role} accounts can do this."), 403
            g.user = user
            return fn(*args, **kwargs)
        return inner
    return wrap


# --------------------------------------------------------------------------
# 4. Serializers. Notice what is NOT here: email is never selected for
#    public mentors, and contact_for() is the only function that reads it.
# --------------------------------------------------------------------------
MENTOR_COLUMNS = "id, name, initials, year, branch, avatar, topics, about, cgpa, availability, sessions, featured"
ACCEPTED_COUNT = "(SELECT COUNT(*) FROM requests r WHERE r.mentor_id = users.id AND r.status = 'accepted')"


def mentor_public(row):
    """Everything a stranger may see about a mentor. No email, no phone, ever."""
    return {
        "id": row["id"], "name": row["name"], "initials": row["initials"], "year": row["year"],
        "branch": row["branch"], "avatar": row["avatar"], "topics": json.loads(row["topics"]),
        "about": row["about"], "cgpa": row["cgpa"], "availability": row["availability"],
        "busy": "capacity" in (row["availability"] or "").lower(),
        "featured": bool(row["featured"]),
        "sessions": row["sessions"] + row["accepted"],   # seed value + real accepted chats
    }


REQUEST_SELECT = """
SELECT r.*,
       j.name AS j_name, j.initials AS j_initials, j.year AS j_year, j.branch AS j_branch,
       m.name AS m_name, m.initials AS m_initials, m.year AS m_year, m.branch AS m_branch,
       m.avatar AS m_avatar, m.topics AS m_topics
FROM requests r
JOIN users j ON j.id = r.junior_id
JOIN users m ON m.id = r.mentor_id
"""


def contact_for(db, row):
    """The ONLY place that reads email addresses for a request."""
    emails = {
        u["id"]: u["email"]
        for u in db.execute("SELECT id, email FROM users WHERE id IN (?, ?)", (row["junior_id"], row["mentor_id"]))
    }
    return {
        "mentorName": row["m_name"], "mentorEmail": emails[row["mentor_id"]],
        "juniorName": row["j_name"], "juniorEmail": emails[row["junior_id"]],
    }


def request_view(db, row, viewer):
    """
    Turns a database row into JSON for ONE viewer.

    Contact details are included only if BOTH are true:
      1. the mentor accepted the request, and
      2. the viewer is the junior or the mentor of THIS request.
    Any other case: the "contact" key simply does not exist in the response.
    """
    out = {
        "id": row["id"], "status": row["status"], "topic": row["topic"], "note": row["message"],
        "tried": row["tried"], "createdAt": row["created_at"], "decidedAt": row["decided_at"],
        "mentorId": row["mentor_id"],
    }
    if viewer["role"] == "junior":
        out["mentor"] = {
            "id": row["mentor_id"], "name": row["m_name"], "initials": row["m_initials"],
            "year": row["m_year"], "branch": row["m_branch"], "avatar": row["m_avatar"],
            "topics": json.loads(row["m_topics"]),
        }
    else:
        # The mentor sees the junior's year and branch, but no name until acceptance.
        out["junior"] = {"initials": row["j_initials"], "year": row["j_year"], "branch": row["j_branch"]}
    if row["status"] == "accepted" and viewer["id"] in (row["junior_id"], row["mentor_id"]):
        out["contact"] = contact_for(db, row)
    return out


# --------------------------------------------------------------------------
# 5. API routes
# --------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def text_field(body, key, limit):
    return str(body.get(key) or "").strip()[:limit]


def register_routes(app):
    @app.get("/api/health")
    def health():
        return jsonify(ok=True, demoMode=current_app.config["DEMO_MODE"])

    # ---- accounts ---------------------------------------------------------
    @app.post("/api/register")
    def register():
        body = request.get_json(silent=True) or {}
        name = text_field(body, "name", 60)
        email = text_field(body, "email", 120).lower()
        password = str(body.get("password") or "")
        domain = current_app.config["ALLOWED_DOMAIN"]
        if len(name) < 2:
            return jsonify(error="Please enter your name."), 400
        if not EMAIL_RE.match(email):
            return jsonify(error="Please enter a valid email."), 400
        if domain and not email.endswith("@" + domain):
            return jsonify(error=f"Please use your college email (@{domain})."), 400
        if len(password) < 8:
            return jsonify(error="Password must be at least 8 characters."), 400
        db = get_db()
        if db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            return jsonify(error="That email is already registered."), 409
        initials = "".join(p[0] for p in name.split()[:2]).upper()
        cur = db.execute(
            "INSERT INTO users (role, name, email, password_hash, year, branch, initials, avatar)"
            " VALUES ('junior', ?, ?, ?, ?, ?, ?, 'slate')",
            (name, email, generate_password_hash(password), text_field(body, "year", 20),
             text_field(body, "branch", 20), initials),
        )
        db.commit()
        return jsonify(token=make_token(cur.lastrowid),
                       user={"id": cur.lastrowid, "name": name, "role": "junior"}), 201

    @app.post("/api/login")
    def login():
        body = request.get_json(silent=True) or {}
        email = text_field(body, "email", 120).lower()
        row = get_db().execute(
            "SELECT id, name, role, password_hash FROM users WHERE email = ?", (email,)
        ).fetchone()
        if row is None or not check_password_hash(row["password_hash"], str(body.get("password") or "")):
            return jsonify(error="Wrong email or password."), 401
        return jsonify(token=make_token(row["id"]),
                       user={"id": row["id"], "name": row["name"], "role": row["role"]})

    @app.get("/api/me")
    @login_required()
    def me():
        return jsonify(g.user)

    # ---- mentors (public) -------------------------------------------------
    @app.get("/api/mentors")
    def list_mentors():
        rows = get_db().execute(
            f"SELECT {MENTOR_COLUMNS}, {ACCEPTED_COUNT} AS accepted FROM users WHERE role = 'mentor' ORDER BY id"
        ).fetchall()
        return jsonify([mentor_public(r) for r in rows])

    @app.get("/api/mentors/<int:mentor_id>")
    def get_mentor(mentor_id):
        row = get_db().execute(
            f"SELECT {MENTOR_COLUMNS}, {ACCEPTED_COUNT} AS accepted FROM users WHERE role = 'mentor' AND id = ?",
            (mentor_id,),
        ).fetchone()
        if row is None:
            return jsonify(error="Mentor not found."), 404
        return jsonify(mentor_public(row))

    @app.patch("/api/me/availability")
    @login_required("mentor")
    def set_availability():
        body = request.get_json(silent=True) or {}
        text = BUSY_TEXT if body.get("busy") else OPEN_TEXT
        db = get_db()
        db.execute("UPDATE users SET availability = ? WHERE id = ?", (text, g.user["id"]))
        db.commit()
        return jsonify(availability=text, busy=bool(body.get("busy")))

    # ---- requests ---------------------------------------------------------
    @app.post("/api/requests")
    @login_required("junior")
    def create_request():
        body = request.get_json(silent=True) or {}
        db = get_db()
        try:
            mentor_id = int(body.get("mentor_id"))
        except (TypeError, ValueError):
            return jsonify(error="Choose a mentor first."), 400
        mentor = db.execute(
            "SELECT id, topics, availability FROM users WHERE id = ? AND role = 'mentor'", (mentor_id,)
        ).fetchone()
        if mentor is None:
            return jsonify(error="Mentor not found."), 404
        if "capacity" in (mentor["availability"] or "").lower():
            return jsonify(error="This mentor is at capacity this week. Please try another mentor."), 409
        if db.execute(
            "SELECT 1 FROM requests WHERE junior_id = ? AND mentor_id = ? AND status IN ('pending', 'accepted')",
            (g.user["id"], mentor_id),
        ).fetchone():
            return jsonify(error="You already have a request with this mentor."), 409
        pending = db.execute(
            "SELECT COUNT(*) FROM requests WHERE junior_id = ? AND status = 'pending'", (g.user["id"],)
        ).fetchone()[0]
        if pending >= MAX_PENDING_PER_JUNIOR:
            return jsonify(error=f"You can have at most {MAX_PENDING_PER_JUNIOR} pending requests."), 429
        topic = text_field(body, "topic", 80) or json.loads(mentor["topics"])[0]
        cur = db.execute(
            "INSERT INTO requests (junior_id, mentor_id, topic, message, tried, status, created_at)"
            " VALUES (?, ?, ?, ?, ?, 'pending', ?)",
            (g.user["id"], mentor_id, topic, text_field(body, "message", 240), text_field(body, "tried", 240), now()),
        )
        db.commit()
        row = db.execute(REQUEST_SELECT + " WHERE r.id = ?", (cur.lastrowid,)).fetchone()
        return jsonify(request_view(db, row, g.user)), 201

    @app.get("/api/requests")
    @login_required()
    def list_requests():
        db = get_db()
        column = "r.junior_id" if g.user["role"] == "junior" else "r.mentor_id"
        sql, args = REQUEST_SELECT + f" WHERE {column} = ?", [g.user["id"]]
        topic = request.args.get("topic")
        if topic:
            sql += " AND r.topic = ?"
            args.append(topic)
        rows = db.execute(sql + " ORDER BY r.created_at DESC, r.id DESC", args).fetchall()
        return jsonify([request_view(db, r, g.user) for r in rows])

    @app.get("/api/requests/<int:request_id>")
    @login_required()
    def get_request(request_id):
        db = get_db()
        row = db.execute(REQUEST_SELECT + " WHERE r.id = ?", (request_id,)).fetchone()
        if row is None:
            return jsonify(error="Request not found."), 404
        if g.user["id"] not in (row["junior_id"], row["mentor_id"]):
            return jsonify(error="This request is not yours."), 403
        return jsonify(request_view(db, row, g.user))

    @app.post("/api/requests/<int:request_id>/decision")
    @login_required("mentor")
    def decide(request_id):
        body = request.get_json(silent=True) or {}
        decision = body.get("decision")
        if decision not in ("accept", "decline"):
            return jsonify(error="decision must be 'accept' or 'decline'."), 400
        db = get_db()
        row = db.execute(REQUEST_SELECT + " WHERE r.id = ?", (request_id,)).fetchone()
        if row is None:
            return jsonify(error="Request not found."), 404
        if row["mentor_id"] != g.user["id"]:
            return jsonify(error="Only the mentor who received this request can answer it."), 403
        if row["status"] != "pending":
            return jsonify(error=f"This request was already {row['status']}."), 409
        status = "accepted" if decision == "accept" else "declined"
        db.execute("UPDATE requests SET status = ?, decided_at = ? WHERE id = ? AND status = 'pending'",
                   (status, now(), request_id))
        db.commit()
        row = db.execute(REQUEST_SELECT + " WHERE r.id = ?", (request_id,)).fetchone()
        return jsonify(request_view(db, row, g.user))

    # ---- demo helpers (only when DEMO_MODE=1) -------------------------------
    @app.post("/api/demo-login")
    def demo_login():
        if not current_app.config["DEMO_MODE"]:
            return jsonify(error="Not found."), 404
        body = request.get_json(silent=True) or {}
        row = get_db().execute(
            "SELECT id, name, role FROM users WHERE id = ?", (body.get("user_id"),)
        ).fetchone()
        if row is None:
            return jsonify(error="Unknown demo account."), 404
        return jsonify(token=make_token(row["id"]),
                       user={"id": row["id"], "name": row["name"], "role": row["role"]})

    @app.post("/api/demo/reset")
    def demo_reset():
        if not current_app.config["DEMO_MODE"]:
            return jsonify(error="Not found."), 404
        seed_db(get_db())
        return jsonify(ok=True)

    # ---- serve the built frontend (used when deployed) ----------------------
    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def frontend(path):
        if path.startswith("api/"):
            return jsonify(error="Not found."), 404
        target = safe_join(DIST_DIR, path) if path else None
        if target and os.path.isfile(target):
            return send_from_directory(DIST_DIR, path)
        if os.path.isfile(os.path.join(DIST_DIR, "index.html")):
            return send_from_directory(DIST_DIR, "index.html")
        return jsonify(message="Mentor Link API is running. Run 'npm run build' in frontend/ to serve the website here.")

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return jsonify(error="Method not allowed."), 405


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
