FROM node:22-bookworm-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 API_PROXY_TARGET=http://127.0.0.1:8000
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv python3-pip ca-certificates && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend/ /app/backend/
COPY frontend/package*.json /app/frontend/
WORKDIR /app/frontend
RUN npm ci || npm install
COPY frontend/ /app/frontend/
RUN npm run build
WORKDIR /app
COPY deploy/start.sh /app/deploy/start.sh
RUN chmod +x /app/deploy/start.sh
EXPOSE 10000
CMD ["/app/deploy/start.sh"]
