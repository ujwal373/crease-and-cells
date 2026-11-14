FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir .

CMD ["sh", "-c", "python -m uvicorn backend.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
