FROM python:3.11-slim

WORKDIR /app

# Dependências de sistema necessárias para pdf2image (poppler) e psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
