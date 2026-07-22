import asyncio
from types import SimpleNamespace

from telos.interfaces.cli import CLI


class FakeService:
    def __init__(self):
        self.created = 0

    async def create_chat(self):
        self.created += 1
        return SimpleNamespace(id="chat-1")

    async def send_message(self, chat_id, content):
        return SimpleNamespace(content=f"reply: {content}")

    async def list_chats(self):
        return [SimpleNamespace(id="chat-1", title="First")]

    async def retry(self, chat_id):
        return SimpleNamespace(content="retried")


def test_new_chat_is_created_lazily():
    output = []
    service = FakeService()
    cli = CLI(service, output_fn=output.append)
    asyncio.run(cli.handle("/new"))
    assert service.created == 0
    asyncio.run(cli.handle("hello"))
    assert service.created == 1
    assert output[-1] == "reply: hello"


def test_resume_uses_list_position():
    output = []
    cli = CLI(FakeService(), output_fn=output.append)
    asyncio.run(cli.handle("/chats"))
    asyncio.run(cli.handle("/resume 1"))
    assert cli.current_chat_id == "chat-1"


def test_retry_requires_a_current_chat():
    output = []
    cli = CLI(FakeService(), output_fn=output.append)
    asyncio.run(cli.handle("/retry"))
    assert output == ["No current chat to retry."]


def test_retry_and_unknown_command_are_reported():
    output = []
    cli = CLI(FakeService(), output_fn=output.append)
    cli.current_chat_id = "chat-1"
    asyncio.run(cli.handle("/retry"))
    asyncio.run(cli.handle("/wat"))
    assert output[0] == "retried"
    assert output[1].startswith("Unknown command.")


def test_invalid_resume_and_service_failure_are_reported():
    output = []
    service = FakeService()
    cli = CLI(service, output_fn=output.append)
    asyncio.run(cli.handle("/resume 3"))

    async def fail(*_):
        raise RuntimeError("unavailable")

    service.send_message = fail
    asyncio.run(cli.handle("hello"))
    assert output == ["Run /chats, then use /resume <number>.", "Error: unavailable"]


def test_run_exits_cleanly_on_end_of_input():
    output = []

    def end_input(_):
        raise EOFError

    asyncio.run(CLI(FakeService(), input_fn=end_input, output_fn=output.append).run())
    assert output[0].startswith("Telos.")
    assert output[-1] == "\nGoodbye."


def test_run_dispatches_non_empty_input_before_exiting():
    output = []
    service = FakeService()
    inputs = iter(["  hello  "])

    def next_input(_):
        try:
            return next(inputs)
        except StopIteration:
            raise EOFError from None

    asyncio.run(CLI(service, input_fn=next_input, output_fn=output.append).run())

    assert service.created == 1
    assert output[1] == "reply: hello"


def test_resume_without_a_number_lists_chats_and_help_is_displayed():
    output = []
    cli = CLI(FakeService(), output_fn=output.append)

    asyncio.run(cli.handle("/resume"))
    asyncio.run(cli.handle("/help"))

    assert output[0].startswith("1. First")
    assert output[-1].startswith("Commands:")


def test_retry_error_is_displayed():
    output = []
    service = FakeService()

    async def fail(_):
        raise RuntimeError("provider down")

    service.retry = fail
    cli = CLI(service, output_fn=output.append)
    cli.current_chat_id = "chat-1"

    asyncio.run(cli.handle("/retry"))

    assert output == ["Error: provider down"]
