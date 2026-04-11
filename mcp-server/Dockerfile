FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml ./
RUN uv sync --frozen --no-dev

COPY . .

ENV DB_PATH=/data/memories.db

CMD ["uv", "run", "python", "main.py"]
