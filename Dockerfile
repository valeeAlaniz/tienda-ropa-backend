FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src ./src
EXPOSE 8000
CMD ["sh", "-c", ".venv/bin/python src/manage.py migrate && exec .venv/bin/python src/manage.py runserver 0.0.0.0:8000 --noreload"]
