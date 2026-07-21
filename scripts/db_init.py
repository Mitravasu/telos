"""Initialize application and LangGraph schemas explicitly."""

from langgraph.checkpoint.postgres import PostgresSaver

from telos.config import database_url_from_env


def main() -> None:
    database_url = database_url_from_env()
    checkpoint_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    with PostgresSaver.from_conn_string(checkpoint_url) as checkpointer:
        checkpointer.setup()


if __name__ == "__main__":
    main()
