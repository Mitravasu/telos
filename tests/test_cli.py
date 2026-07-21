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
