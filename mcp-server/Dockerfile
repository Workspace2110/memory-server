FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

ENV FASTEMBED_CACHE_PATH=/app/.cache/fastembed

CMD ["uv", "run", "python", "main.py"]
