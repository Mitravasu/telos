FROM ghcr.io/astral-sh/uv:0.10.9 AS uv
FROM python:3.12-slim

COPY --from=uv /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY . .
RUN uv sync --locked --no-dev
ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT ["telos"]
