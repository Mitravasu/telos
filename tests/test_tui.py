import asyncio
from types import SimpleNamespace
from uuid import uuid4

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

from telos.interfaces.tui import TelosApp


class FakeService:
    def __init__(self):
        self.chat_id = uuid4()
        self.created = 0
        self.messages = [HumanMessage(content="old question"), AIMessage(content="old answer")]
        self.block = asyncio.Event()

    async def create_chat(self):
        self.created += 1
        return SimpleNamespace(id=self.chat_id)

    async def list_chats(self):
        return [SimpleNamespace(id=self.chat_id, title="Existing chat")]

    async def get_messages(self, chat_id):
        assert chat_id == self.chat_id
        return self.messages

    async def stream_message(self, chat_id, content):
        assert chat_id == self.chat_id
        yield AIMessageChunk(content="streamed ")
        yield AIMessageChunk(content="answer")
        yield AIMessage(content="streamed answer")

    async def stream_retry(self, chat_id):
        assert chat_id == self.chat_id
        yield AIMessageChunk(content="retry")
        yield AIMessage(content="retry")


def transcript_text(app):
    return "\n".join(str(child.render()) for child in app.query_one("#transcript").children)


def test_tui_streams_a_new_message_and_supports_commands():
    async def exercise():
        service = FakeService()
        app = TelosApp(service)
        async with app.run_test() as pilot:
            await pilot.press("h", "i", "enter")
            await app._generation_worker.wait()
            assert service.created == 1
            assert "hi" in transcript_text(app)
            assert "streamed answer" in transcript_text(app)

            await pilot.press("/", "r", "e", "t", "r", "y", "enter")
            await app._generation_worker.wait()
            assert "retry" in transcript_text(app)

            await pilot.press("/", "n", "e", "w", "enter")
            assert app.current_chat_id is None
            assert not app.query_one("#transcript").children

    asyncio.run(exercise())


def test_tui_picker_redraws_persisted_history_and_escape_closes_it():
    async def exercise():
        app = TelosApp(FakeService())
        async with app.run_test() as pilot:
            await pilot.press("/", "r", "e", "s", "u", "m", "e", "enter")
            assert app.query_one("#picker").display
            await pilot.press("escape")
            assert not app.query_one("#picker").display

            await app._open_picker()
            picker = app.query_one("#picker")
            picker.index = 0
            await app.on_list_view_selected(SimpleNamespace(list_view=picker))
            assert app.current_chat_id == app.service.chat_id
            assert "old question" in transcript_text(app)
            assert "old answer" in transcript_text(app)

    asyncio.run(exercise())


def test_tui_cancels_an_active_generation():
    class BlockingService(FakeService):
        def __init__(self):
            super().__init__()
            self.started = asyncio.Event()

        async def stream_message(self, chat_id, content):
            try:
                self.started.set()
                await asyncio.Event().wait()
            finally:
                self.block.set()
            yield AIMessage(content="unreachable")

    async def exercise():
        service = BlockingService()
        app = TelosApp(service)
        async with app.run_test() as pilot:
            await pilot.press("h", "i", "enter")
            await service.started.wait()
            app.action_interrupt()
            await pilot.pause()
            assert service.block.is_set()

    asyncio.run(exercise())
