# Automated Resume Parser (Flask + spaCy + PostgreSQL)

Extracts candidate details (name, email, phone, skills, education, summary/experience) from PDF/DOCX/TXT resumes and stores them in a searchable PostgreSQL database.

## Stack
- Python 3.11, Flask
- spaCy (en_core_web_sm)
- PDFPlumber (PDF), python-docx (DOCX)
- PostgreSQL + SQLAlchemy

## Quick Start (Docker)
```bash
cp .env.example .env
docker compose up --build
