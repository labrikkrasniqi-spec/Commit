from datetime import datetime
from pathlib import Path
import sqlite3

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "commit.db"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder=str(BASE_DIR))

OPPORTUNITIES = [
    ("Internship", "Software Engineering Intern", "Astra Labs", "Remote", "2026-10-15", "Work on platform features, bug fixes, and product improvements.", "software,engineering,javascript,python,backend,frontend,api,full stack,product"),
    ("Workshop", "AI Product Design Sprint", "Northstar Studio", "Hybrid", "2026-09-28", "Learn product thinking and craft AI-powered user experiences.", "design,product,ai,ux,prototype,workshop,wireframes"),
    ("Hackathon", "Climate Tech Challenge", "GreenGrid", "In Person", "2026-11-04", "Build sustainable solutions with real-world climate datasets.", "hackathon,climate,sustainability,ai,data,prototype,innovation"),
    ("Internship", "Data Analyst Intern", "Pulse Metrics", "Remote", "2026-10-01", "Analyze campaigns, prepare dashboards, and generate business insights.", "data,analytics,sql,python,dashboard,statistics,research"),
    ("Workshop", "Cybersecurity Fundamentals Lab", "Signal Forge", "Online", "2026-10-12", "Practice secure coding, threat modeling, and defensive design.", "cybersecurity,security,network,threat modeling,workshop,ethical hacking"),
    ("Hackathon", "OpenAI for Good Hackathon", "Civic Forge", "Remote", "2026-10-25", "Create AI-powered solutions for communities and public services.", "ai,hackathon,ml,community,innovation,python"),
    ("Internship", "UX Research Intern", "Nova Interface", "Hybrid", "2026-09-30", "Research user pain points and translate findings into product decisions.", "ux,research,design,product,user testing,interviews"),
    ("Workshop", "Agile Product Strategy Bootcamp", "LaunchForge", "In Person", "2026-11-18", "Build product roadmaps through sprint planning exercises.", "product,strategy,agile,workshop,planning,execution"),
]

COMPANY_ACCOUNT = {
    "organization_id": "ORG-COMMIT-2026",
    "security_token": "commit-enterprise-demo",
    "name": "Commit Partner Network",
}

APPLICANTS = [
    ("Aisha Mensah", "Software Engineering Intern", "aisha.mensah@example.com", "92% match", "Reviewing"),
    ("Daniel Okafor", "Data Analyst Intern", "daniel.okafor@example.com", "88% match", "Shortlisted"),
    ("Maya Chen", "AI Product Design Sprint", "maya.chen@example.com", "84% match", "New"),
]


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_db() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT NOT NULL,
                linkedin TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT NOT NULL,
                deadline TEXT NOT NULL,
                description TEXT NOT NULL,
                keywords TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS "references" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                type TEXT NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                filename TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(student_id) REFERENCES students(id)
            );
            CREATE TABLE IF NOT EXISTS applicants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                opportunity TEXT NOT NULL,
                email TEXT NOT NULL,
                match_score TEXT NOT NULL,
                status TEXT NOT NULL
            );
        """)
        connection.execute(
            "INSERT OR IGNORE INTO students (email, password, name) VALUES (?, ?, ?)",
            ("student@commit.com", "student123", "Aisha"),
        )
        if connection.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO opportunities (type,title,company,location,deadline,description,keywords) VALUES (?,?,?,?,?,?,?)",
                OPPORTUNITIES,
            )
        if connection.execute('SELECT COUNT(*) FROM "references"').fetchone()[0] == 0:
            connection.executemany(
            'INSERT INTO "references" (title,type,status) VALUES (?,?,?)',
                [("Recommendation - Dr. Mensah", "Professor", "Verified"),
                 ("Mentorship Letter - Mr. Chen", "Lecturer", "Pending"),
                 ("Academic Endorsement - Prof. Okafor", "Professor", "Verified")],
            )
        if connection.execute("SELECT COUNT(*) FROM applicants").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO applicants (name,opportunity,email,match_score,status) VALUES (?,?,?,?,?)",
                APPLICANTS,
            )


def student_from_request():
    student_id = request.headers.get("X-Student-ID")
    if not student_id or not student_id.isdigit():
        return None
    with get_db() as connection:
        return connection.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()


@app.get("/")
def index():
    return send_from_directory(BASE_DIR, "Commit.html")


@app.post("/api/login")
def login():
    payload = request.get_json(silent=True) or {}
    with get_db() as connection:
        student = connection.execute(
            "SELECT id, email, name FROM students WHERE lower(email) = lower(?) AND password = ?",
            (payload.get("email", ""), payload.get("password", "")),
        ).fetchone()
    if not student:
        return jsonify({"error": "Invalid student credentials"}), 401
    return jsonify(dict(student))


@app.post("/api/demo-student-login")
def demo_student_login():
    with get_db() as connection:
        student = connection.execute("SELECT id, email, name FROM students WHERE email = ?", ("student@commit.com",)).fetchone()
    return jsonify(dict(student))


@app.post("/api/company/login")
def company_login():
    payload = request.get_json(silent=True) or {}
    if (payload.get("organizationId") != COMPANY_ACCOUNT["organization_id"] or
            payload.get("securityToken") != COMPANY_ACCOUNT["security_token"]):
        return jsonify({"error": "Invalid organization credentials"}), 401
    return jsonify({"organizationId": COMPANY_ACCOUNT["organization_id"], "name": COMPANY_ACCOUNT["name"]})


@app.post("/api/company/demo-login")
def company_demo_login():
    return jsonify({"organizationId": COMPANY_ACCOUNT["organization_id"], "name": COMPANY_ACCOUNT["name"]})


@app.get("/api/opportunities")
def opportunities():
    query = request.args.get("q", "").strip().lower()
    with get_db() as connection:
        rows = connection.execute("SELECT * FROM opportunities ORDER BY deadline").fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["keywords"] = item["keywords"].split(",")
        searchable = " ".join(str(value) for value in item.values()).lower()
        if not query or query in searchable:
            result.append(item)
    return jsonify(result)


@app.post("/api/company/opportunities")
def create_opportunity():
    if request.headers.get("X-Organization-ID") != COMPANY_ACCOUNT["organization_id"]:
        return jsonify({"error": "Company authentication required"}), 401
    payload = request.get_json(silent=True) or {}
    required = ("type", "title", "company", "location", "deadline", "description")
    if any(not payload.get(field) for field in required):
        return jsonify({"error": "All opportunity fields are required"}), 400
    keywords = payload.get("keywords", "")
    if isinstance(keywords, list):
        keywords = ",".join(keywords)
    with get_db() as connection:
        cursor = connection.execute(
            "INSERT INTO opportunities (type,title,company,location,deadline,description,keywords) VALUES (?,?,?,?,?,?,?)",
            tuple(payload[field] for field in required) + (keywords,),
        )
    return jsonify({"id": cursor.lastrowid}), 201


@app.get("/api/company/applicants")
def applicants():
    if request.headers.get("X-Organization-ID") != COMPANY_ACCOUNT["organization_id"]:
        return jsonify({"error": "Company authentication required"}), 401
    with get_db() as connection:
        rows = connection.execute("SELECT * FROM applicants ORDER BY id").fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/references")
def references():
    with get_db() as connection:
        rows = connection.execute('SELECT * FROM "references" ORDER BY id').fetchall()
    return jsonify([dict(row) for row in rows])


@app.post("/api/references/<int:reference_id>/endorse")
def endorse(reference_id):
    if not student_from_request():
        return jsonify({"error": "Authentication required"}), 401
    with get_db() as connection:
        connection.execute('UPDATE "references" SET status = \'Endorsed by Lecturer\' WHERE id = ?', (reference_id,))
    return jsonify({"status": "Endorsed by Lecturer"})


@app.post("/api/profile")
def profile():
    student = student_from_request()
    if not student:
        return jsonify({"error": "Authentication required"}), 401
    linkedin = request.form.get("linkedin", "")
    with get_db() as connection:
        connection.execute("UPDATE students SET linkedin = ? WHERE id = ?", (linkedin, student["id"]))
        for category in ("cv", "certificates"):
            for uploaded in request.files.getlist(category):
                if not uploaded.filename:
                    continue
                filename = secure_filename(uploaded.filename)
                uploaded.save(UPLOAD_DIR / f"{student['id']}_{category}_{filename}")
                connection.execute(
                    "INSERT INTO uploads (student_id, category, filename, created_at) VALUES (?, ?, ?, ?)",
                    (student["id"], category, filename, datetime.utcnow().isoformat()),
                )
    return jsonify({"saved": True})


if __name__ == "__main__":
    initialize_database()
    app.run(debug=True, port=5000)
