# [CODEX_ENHANCEMENT_2026-11-21] No third-party runtime dependencies.
FROM python:3.13.9-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /bot
COPY bot.py mechfight.py ./
COPY agent ./agent
USER 65534:65534
ENTRYPOINT ["python3", "-u", "/bot/bot.py"]
