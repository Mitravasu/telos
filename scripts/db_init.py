"""Initialize application and LangGraph schemas explicitly."""

from langgraph.checkpoint.postgres import PostgresSaver

from telos.config import Settings


def main() -> None:
    settings = Settings.from_env()
    with PostgresSaver.from_conn_string(settings.checkpoint_database_url) as checkpointer:
        checkpointer.setup()


if __name__ == "__main__":
    main()
