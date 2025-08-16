FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc poppler-utils && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && python -m spacy download en_core_web_sm

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["bash", "-lc", "mkdir -p ${UPLOAD_DIR:-./uploads} && python app.py"]
