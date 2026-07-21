# Telos

A persistent terminal career agent.

## Quick start

```sh
cp .env.example .env
make dev
```

Set `OLLAMA_MODEL` in `.env`. `make dev` starts PostgreSQL, initializes both schemas, then runs the host CLI.
