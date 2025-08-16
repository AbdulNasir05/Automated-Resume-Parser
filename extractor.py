import re
from pathlib import Path
from typing import Dict, List, Tuple
import pdfplumber
import docx
import spacy
from rapidfuzz import process, fuzz

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(\+?\d{1,3}[\s.-]?)?(\(?\d{3,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4}")
DEGREE_TERMS = [
    "bachelor", "master", "phd", "doctor", "b.tech", "btech", "m.tech", "mtech",
    "b.sc", "bsc", "m.sc", "msc", "b.e", "be", "m.e", "me", "mba", "bca", "mca"
]

nlp = spacy.load("en_core_web_sm")

def read_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        with pdfplumber.open(path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    if ext == ".docx":
        d = docx.Document(str(path))
        return "\n".join(p.text for p in d.paragraphs)
    if ext == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"Unsupported file type: {ext}")

def extract_name(doc: spacy.tokens.Doc) -> str | None:
    # Prefer topmost PERSON entity that isn't an email/phone fragment
    persons = [ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON"]
    return persons[0] if persons else None

def extract_email(text: str) -> str | None:
    m = EMAIL_RE.search(text)
    return m.group(0) if m else None

def extract_phone(text: str) -> str | None:
    candidates = PHONE_RE.findall(text)
    if not candidates:
        return None
    # Flatten and choose the longest match
    raw = max(["".join(t) for t in candidates], key=len)
    # Normalize
    digits = re.sub(r"[^\d+]", "", raw)
    return digits

def extract_location(doc: spacy.tokens.Doc) -> str | None:
    gpes = [ent.text.strip() for ent in doc.ents if ent.label_ in {"GPE", "LOC"}]
    return gpes[0] if gpes else None

def split_sections(text: str) -> Tuple[str, str, str]:
    t = text.lower()
    # Heuristic splits; robust enough for MVP
    edu_idx = t.find("education")
    exp_idx = max(t.find("experience"), t.find("employment"))
    education = text[edu_idx:] if edu_idx != -1 else ""
    experience = text[exp_idx:] if exp_idx != -1 else ""
    summary = text[: min([i for i in [edu_idx, exp_idx] if i != -1], default=len(text))]
    return summary.strip(), education.strip(), experience.strip()

def load_skills(path: Path) -> List[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def fuzzy_skill_match(text: str, skills: List[str]) -> List[str]:
    found = set()
    for sk, score, _ in process.extract(text, skills, scorer=fuzz.token_set_ratio, score_cutoff=85, limit=200):
        found.add(sk)
    # Also exact lower-case contains for simple tokens
    lt = text.lower()
    for sk in skills:
        token = sk.lower()
        if re.search(rf"\b{re.escape(token)}\b", lt):
            found.add(sk)
    return sorted(found)

def extract_all(path: Path, skills_path: Path) -> Dict:
    text = read_text(path)
    doc = nlp(text)

    summary, education, experience = split_sections(text)
    skills = load_skills(skills_path)
    matched_skills = fuzzy_skill_match(text, skills)

    data = {
        "name": extract_name(doc),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "location": extract_location(doc),
        "summary": summary,
        "education_text": education,
        "experience_text": experience,
        "skills": {"matched": matched_skills},
        "raw_text": text
    }
    return data
