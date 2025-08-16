import os
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from database import engine, Base, get_session
from models import Candidate
from config import settings
from parser.extractor import extract_all

app = Flask(__name__)
app.config["SECRET_KEY"] = settings.SECRET_KEY
UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
Base.metadata.create_all(bind=engine)

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in settings.ALLOWED_EXTENSIONS

@app.post("/upload")
def upload_resume():
    if "file" not in request.files:
        return jsonify({"error": "file is required"}), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "empty filename"}), 400
    if not allowed_file(f.filename):
        return jsonify({"error": f"Unsupported type. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"}), 400

    filename = secure_filename(f.filename)
    dest = UPLOAD_DIR / filename
    f.save(dest)

    data = extract_all(dest, Path("parser/skills.txt"))

    with Session(engine) as db:
        cand = Candidate(
            name=data.get("name"),
            email=data.get("email"),
            phone=data.get("phone"),
            location=data.get("location"),
            summary=data.get("summary"),
            education_text=data.get("education_text"),
            experience_text=data.get("experience_text"),
            skills=data.get("skills"),
            source_filename=filename,
            raw_text=data.get("raw_text"),
        )
        db.add(cand)
        db.commit()
        db.refresh(cand)

    return jsonify({"id": cand.id, "message": "parsed and stored"}), 201

@app.get("/candidates")
def list_candidates():
    page = int(request.args.get("page", 1))
    size = min(int(request.args.get("size", 20)), 100)
    offset = (page - 1) * size
    with Session(engine) as db:
        q = db.scalars(select(Candidate).order_by(Candidate.created_at.desc()).offset(offset).limit(size)).all()
        return jsonify([serialize(c) for c in q])

@app.get("/candidates/<int:candidate_id>")
def get_candidate(candidate_id: int):
    with Session(engine) as db:
        cand = db.get(Candidate, candidate_id)
        if not cand:
            return jsonify({"error": "not found"}), 404
        return jsonify(serialize(cand))

@app.get("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "q is required"}), 400
    like = f"%{q}%"
    with Session(engine) as db:
        stmt = select(Candidate).where(
            or_(
                Candidate.name.ilike(like),
                Candidate.email.ilike(like),
                Candidate.phone.ilike(like),
                Candidate.location.ilike(like),
                Candidate.summary.ilike(like),
                Candidate.education_text.ilike(like),
                Candidate.experience_text.ilike(like),
            )
        ).order_by(Candidate.created_at.desc()).limit(100)
        rows = db.scalars(stmt).all()
        return jsonify([serialize(c) for c in rows])

@app.get("/uploads/<path:filename>")
def uploaded_file(filename):
    # Serve stored files if needed (only for internal/dev usage)
    return send_from_directory(UPLOAD_DIR, filename)

def serialize(c: Candidate) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "email": c.email,
        "phone": c.phone,
        "location": c.location,
        "skills": c.skills,
        "summary": c.summary,
        "education_text": c.education_text,
        "experience_text": c.experience_text,
        "source_filename": c.source_filename,
        "created_at": c.created_at.isoformat(timespec="seconds"),
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_ENV") == "development")
