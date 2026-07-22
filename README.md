# Telos

A persistent terminal career agent.

## Quick start

```sh
cp .env.example .env
make dev
```

Set `OLLAMA_MODEL` in `.env`. `make dev` starts PostgreSQL, initializes both schemas, then runs the host CLI.

## Observability

Set `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, and `LANGFUSE_BASE_URL` in `.env`. Every graph invocation is traced with the Telos user ID and chat ID as its Langfuse user and session IDs.
