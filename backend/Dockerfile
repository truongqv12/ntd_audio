FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic
COPY src /app/src
COPY catalogs /app/catalogs

ENV PYTHONPATH=/app/src

CMD ["uvicorn", "voiceforge.main:app", "--host", "0.0.0.0", "--port", "8000"]
