FROM node:22-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci || npm install
COPY . .
ARG API_PROXY_TARGET=http://api:8000
ENV API_PROXY_TARGET=${API_PROXY_TARGET}
RUN npm run build
CMD ["npm","run","start"]
