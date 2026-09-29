FROM python:3.12.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --requirement requirements.txt

RUN groupadd --gid 10001 bot \
    && useradd --uid 10001 --gid bot --create-home --shell /usr/sbin/nologin bot \
    && mkdir --parents /app/.data \
    && chown --recursive bot:bot /app

COPY --chown=bot:bot . .

USER bot

STOPSIGNAL SIGTERM

CMD ["python", "main.py"]
