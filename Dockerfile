FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt \
    && python -c "import gunicorn; print('Gunicorn installed:', gunicorn.__version__)"

COPY . .

CMD ["sh", "-c", "exec python -m gunicorn app:app --bind 0.0.0.0:${PORT:-10000}"]
