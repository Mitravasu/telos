from contextlib import nullcontext
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
    monkeypatch.setattr(
        telos.main,
        "PostgresSaver",
        SimpleNamespace(from_conn_string=lambda url: nullcontext(captured.setdefault("checkpoint", url))),
    )
    monkeypatch.setattr(telos.main, "build_graph", lambda model, checkpoint: (model, checkpoint))
    monkeypatch.setattr(telos.main, "ChatService", lambda session, graph: (session, graph))

    class FakeCLI:
        def __init__(self, service):
            captured["service"] = service

        def run(self):
            captured["ran"] = True

    monkeypatch.setattr(telos.main, "CLI", FakeCLI)
    telos.main.main()

    assert captured["engine"] == settings.database_url
    assert captured["checkpoint"] == "postgresql://u:p@db/telos"
    assert captured["model"].client_kwargs == {"headers": {"Authorization": "Bearer key"}}
    assert captured["ran"] is True
