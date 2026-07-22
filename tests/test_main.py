import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import telos.main
from telos.config import Settings


def test_main_composes_cloud_dependencies(monkeypatch):
    settings = Settings("postgresql+psycopg://u:p@db/telos", "https://ollama.com", "model", "key")
    captured = {}

    monkeypatch.setattr(telos.main.Settings, "from_env", lambda: settings)
    monkeypatch.setattr(telos.main, "create_sync_engine", lambda url: captured.setdefault("engine", url))
    monkeypatch.setattr(telos.main, "create_session_factory", lambda engine: captured.setdefault("session", engine))
    monkeypatch.setattr(
        telos.main,
        "ChatOllama",
        lambda **kwargs: captured.setdefault("model", SimpleNamespace(**kwargs)),
    )
    handler = object()
    langfuse = SimpleNamespace(flush=lambda: captured.setdefault("flushed", True))
    monkeypatch.setattr(telos.main, "get_client", lambda: langfuse)
    monkeypatch.setattr(telos.main, "CallbackHandler", lambda: handler)
    @asynccontextmanager
    async def checkpointer_context(url):
        async def setup():
            captured["setup"] = True

        captured["checkpoint"] = url
        yield SimpleNamespace(setup=setup)

    monkeypatch.setattr(
        telos.main,
        "AsyncPostgresSaver",
        SimpleNamespace(from_conn_string=checkpointer_context),
    )
    monkeypatch.setattr(telos.main, "build_graph", lambda model, checkpoint: (model, checkpoint))
    monkeypatch.setattr(
        telos.main, "ChatService", lambda session, graph, callbacks: (session, graph, callbacks)
    )

    class FakeApp:
        def __init__(self, service):
            captured["service"] = service

        async def run_async(self):
            captured["ran"] = True

    monkeypatch.setattr(telos.main, "TelosApp", FakeApp)
    asyncio.run(telos.main.run())

    assert captured["engine"] == settings.database_url
    assert captured["checkpoint"] == "postgresql://u:p@db/telos"
    assert captured["setup"] is True
    assert captured["model"].client_kwargs == {"headers": {"Authorization": "Bearer key"}}
    assert captured["service"][2] == [handler]
    assert captured["ran"] is True
    assert captured["flushed"] is True
