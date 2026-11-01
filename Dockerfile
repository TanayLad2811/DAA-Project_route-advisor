# -------------------------------------------------------------
# Stage 1: Build Frontend (Vite + React + TypeScript)
# -------------------------------------------------------------
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# -------------------------------------------------------------
# Stage 2: Production Python Backend with OpenCV & PyMuPDF
# -------------------------------------------------------------
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies required for OpenCV and PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ ./

# Copy built frontend from Stage 1 into backend/static
COPY --from=frontend-builder /app/frontend/dist ./static

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
