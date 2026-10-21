# GoEye API image for Docker hosts (the live API runs on Render via the Procfile).
# Listens on $PORT when the platform sets it, otherwise 7860.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd --create-home --uid 1000 user

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# The pipeline writes raw/, staging/ and pipeline.log next to the code,
# so the app directory must belong to the runtime user.
COPY --chown=user:user . .
RUN mkdir -p raw staging && chown user:user /app raw staging

USER user

EXPOSE 7860
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
