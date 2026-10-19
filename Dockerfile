# GoEye API image for Hugging Face Spaces (Docker SDK).
# Spaces run the container as uid 1000 and route traffic to app_port 7860.
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
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
