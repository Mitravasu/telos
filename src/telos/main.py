"""Telos application composition root."""

from contextlib import ExitStack

from langchain_ollama import ChatOllama
from langgraph.checkpoint.postgres import PostgresSaver

from telos.agents.orchestrator import build_graph
from telos.config import Settings
from telos.db.session import create_session_factory, create_sync_engine
from telos.interfaces.cli import CLI
from telos.services.chat import ChatService


def main() -> None:
    settings = Settings.from_env()
    engine = create_sync_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    model = ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        client_kwargs={"headers": {"Authorization": f"Bearer {settings.ollama_api_key}"}}
        if settings.ollama_api_key
        else {},
    )

    with ExitStack() as stack:
        checkpointer = stack.enter_context(PostgresSaver.from_conn_string(settings.checkpoint_database_url))
        graph = build_graph(model, checkpointer)
        service = ChatService(session_factory, graph)
        CLI(service).run()


if __name__ == "__main__":
    main()
