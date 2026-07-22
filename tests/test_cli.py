from types import SimpleNamespace

from telos.interfaces.cli import CLI


class FakeService:
    def __init__(self):
        self.created = 0

    def create_chat(self):
        self.created += 1
        return SimpleNamespace(id="chat-1")

    def send_message(self, chat_id, content):
        return SimpleNamespace(content=f"reply: {content}")

    def list_chats(self):
        return [SimpleNamespace(id="chat-1", title="First")]

    def retry(self, chat_id):
        return SimpleNamespace(content="retried")


def test_new_chat_is_created_lazily():
    output = []
    service = FakeService()
    cli = CLI(service, output_fn=output.append)
    cli.handle("/new")
    assert service.created == 0
    cli.handle("hello")
    assert service.created == 1
    assert output[-1] == "reply: hello"


def test_resume_uses_list_position():
    output = []
    cli = CLI(FakeService(), output_fn=output.append)
    cli.handle("/chats")
    cli.handle("/resume 1")
    assert cli.current_chat_id == "chat-1"


def test_retry_requires_a_current_chat():
    output = []
    cli = CLI(FakeService(), output_fn=output.append)
    cli.handle("/retry")
    assert output == ["No current chat to retry."]


def test_retry_and_unknown_command_are_reported():
    output = []
    cli = CLI(FakeService(), output_fn=output.append)
    cli.current_chat_id = "chat-1"
    cli.handle("/retry")
    cli.handle("/wat")
    assert output[0] == "retried"
    assert output[1].startswith("Unknown command.")


def test_invalid_resume_and_service_failure_are_reported():
    output = []
    service = FakeService()
    cli = CLI(service, output_fn=output.append)
    cli.handle("/resume 3")

    def fail(*_):
        raise RuntimeError("unavailable")

    service.send_message = fail
    cli.handle("hello")
    assert output == ["Run /chats, then use /resume <number>.", "Error: unavailable"]


def test_run_exits_cleanly_on_end_of_input():
    output = []

    def end_input(_):
        raise EOFError

    CLI(FakeService(), input_fn=end_input, output_fn=output.append).run()
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

    CLI(service, input_fn=next_input, output_fn=output.append).run()

    assert service.created == 1
    assert output[1] == "reply: hello"


def test_resume_without_a_number_lists_chats_and_help_is_displayed():
    output = []
    cli = CLI(FakeService(), output_fn=output.append)

    cli.handle("/resume")
    cli.handle("/help")

    assert output[0].startswith("1. First")
    assert output[-1].startswith("Commands:")


def test_retry_error_is_displayed():
    output = []
    service = FakeService()
    service.retry = lambda _: (_ for _ in ()).throw(RuntimeError("provider down"))
    cli = CLI(service, output_fn=output.append)
    cli.current_chat_id = "chat-1"

    cli.handle("/retry")

    assert output == ["Error: provider down"]
