FROM python:3.13-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements_web.txt
ENV PORT=8080
CMD uvicorn web_app:app --host 0.0.0.0 --port ${PORT}
