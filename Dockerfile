FROM python:3.13-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements_web.txt
ENV PORT=8080
# Entrada de producción: evita un segundo intérprete completo durante cargas Excel.
CMD uvicorn server_entry:app --host 0.0.0.0 --port ${PORT} --workers 1
