# syntax=docker/dockerfile:1.7
FROM node:24-alpine AS frontend-deps
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

FROM frontend-deps AS frontend-dev
COPY frontend/ ./
CMD ["npm", "run", "dev"]

FROM frontend-deps AS frontend-build
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS backend-base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app
WORKDIR /app
COPY backend/requirements.txt backend/requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./

FROM backend-base AS backend-dev
RUN pip install --no-cache-dir -r requirements-dev.txt
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM backend-base AS production
COPY --from=frontend-build /frontend/dist /app/static
ENV ENVIRONMENT=production \
    FRONTEND_DIST=/app/static \
    PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

