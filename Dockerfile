# BSG Hoarding app for a server (Render): the engine (Python + LibreOffice for xlsx -> pdf, DejaVu fonts) and the web app.
# README, "Deploy on Render". The data folder is the server's disk at /var/data (users, jobs, runs, the audit).
FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BSG_DEPLOY=1 \
    BSG_DATA=/var/data \
    HOME=/tmp

RUN apt-get update \
 && apt-get install -y --no-install-recommends libreoffice-calc-nogui fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/bsg
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Render sets PORT (deploy mode listens on 0.0.0.0:$PORT); 10000 when it doesn't.
ENV PORT=10000
EXPOSE 10000
CMD ["python", "-m", "app"]
