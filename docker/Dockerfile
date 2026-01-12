# ---- base image ----
FROM python:3.11-slim

# ---- prevent python from being weird ----
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ---- set workdir ----
WORKDIR /app

# ---- system deps (psycopg2 needs this) ----
RUN apt-get update \
    && apt-get install -y gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ---- install python deps first (layer caching) ----
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- copy app code ----
COPY . .

# ---- expose fastapi port ----
EXPOSE 8000

# ---- run server ----
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]