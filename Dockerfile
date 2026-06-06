FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Sobe a API por padrão
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]