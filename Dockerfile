FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

RUN groupadd --system --gid 10001 mlai \
    && useradd --system --uid 10001 --gid mlai --home-dir /app mlai

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --requirement requirements.txt

COPY app ./app
COPY deployment ./deployment
COPY assets ./assets
COPY prompts ./prompts

RUN mkdir -p /tmp/mlai/database /tmp/mlai/backups /tmp/mlai/outputs \
    && chown -R mlai:mlai /app /tmp/mlai

USER 10001:10001
EXPOSE 8080

CMD ["python", "-m", "deployment.start"]
