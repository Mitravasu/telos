"""Telos application composition root."""

import asyncio
from contextlib import AsyncExitStack

from langchain_ollama import ChatOllama
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from telos.agents.orchestrator import build_graph
from telos.config import Settings
from telos.db.session import create_session_factory, create_sync_engine
from telos.interfaces.tui import TelosApp
from telos.services.chat import ChatService


async def run() -> None:
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
    langfuse = get_client()
    langfuse_handler = CallbackHandler()

    try:
        async with AsyncExitStack() as stack:
            checkpointer = await stack.enter_async_context(
                AsyncPostgresSaver.from_conn_string(settings.checkpoint_database_url)
            )
            await checkpointer.setup()
            graph = build_graph(model, checkpointer)
            service = ChatService(session_factory, graph, callbacks=[langfuse_handler])
            await TelosApp(service).run_async()
    finally:
        langfuse.flush()


if __name__ == "__main__":
    asyncio.run(run())


def main() -> None:
    asyncio.run(run())
