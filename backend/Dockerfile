FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Cloud Run define PORT; en local se usa 8080.
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
