FROM python:3.13-slim
WORKDIR /app
COPY . /app
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements_web.txt
ENV PORT=8080
# Reduce la fragmentación del heap en el plan Starter de 512 MB.
ENV MALLOC_ARENA_MAX=2
ENV PYTHONUNBUFFERED=1
CMD uvicorn server_entry:app --host 0.0.0.0 --port ${PORT} --workers 1
