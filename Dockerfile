FROM node:20-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NEXT_TELEMETRY_DISABLED=1

RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r /app/backend/requirements.txt

COPY frontend/package.json /app/frontend/package.json
WORKDIR /app/frontend
RUN npm install
COPY frontend/ /app/frontend/
RUN npm run build

WORKDIR /app
COPY backend/ /app/backend/
COPY deploy/start.sh /app/deploy/start.sh
RUN chmod +x /app/deploy/start.sh

ENV PATH="/opt/venv/bin:$PATH"
EXPOSE 10000
CMD ["/app/deploy/start.sh"]
