"""Textual chat interface."""

import asyncio
from uuid import UUID

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Input, ListItem, ListView, Markdown, Static

from telos.interfaces.commands import CommandName, CommandParser


HELP = "Commands: /new, /resume, /retry, /help. Ctrl+C cancels generation or exits."


class TelosApp(App):
    """A command-first, streaming conversation interface."""

    CSS = """
    #transcript { height: 1fr; padding: 1 2; }
    #picker { display: none; height: 1fr; padding: 1 2; }
    #prompt { dock: bottom; }
    .message {
        margin-bottom: 1;
        padding: 1;
        content-align: center middle;
        text-align: center;
    }
    .message > MarkdownParagraph { margin: 0; }
    .user { background: $primary 15%; }
    .assistant { background: $surface; }
    """
    BINDINGS = [("ctrl+c", "interrupt", "Cancel generation / quit"), ("escape", "escape", "Back")]

    def __init__(self, service, **kwargs) -> None:
        super().__init__(**kwargs)
        self.service = service
        self.current_chat_id: UUID | None = None
        self._parser = CommandParser()
        self._picker_chats = []
        self._generation_worker = None
        self._generation_active = False
        self._streaming_message: Markdown | None = None
        self._streamed_content = ""

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="transcript")
        yield ListView(id="picker")
        yield Input(placeholder="Message Telos or type /help", id="prompt")

    async def on_mount(self) -> None:
        self.query_one("#prompt", Input).focus()
        await self._show_help()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        event.input.value = ""
        if not text:
            return
        if self._is_picker_open():
            self.notify("Choose a chat with arrows and Enter, or press Esc.", severity="warning")
            return
        command = self._parser.parse(text)
        if command is None:
            await self._send(text)
        else:
            await self._handle_command(command.name, command.argument)

    async def _handle_command(self, name: CommandName, argument: str) -> None:
        if name is CommandName.NEW:
            self.current_chat_id = None
            await self._clear_transcript()
            self.notify("A new chat will start with your next message.")
        elif name is CommandName.RESUME:
            if argument:
                self.notify("Use /resume, then choose a chat with arrows and Enter.", severity="warning")
            else:
                await self._open_picker()
        elif name is CommandName.RETRY:
            if self.current_chat_id is None:
                self.notify("No current chat to retry.", severity="warning")
            else:
                await self._start_stream(self.service.stream_retry(self.current_chat_id), show_user=None)
        elif name is CommandName.HELP:
            await self._show_help()
        else:
            self.notify(f"Unknown command: {argument}. {HELP}", severity="error")

    async def _send(self, content: str) -> None:
        if self.current_chat_id is None:
            self.current_chat_id = (await self.service.create_chat()).id
        await self._start_stream(self.service.stream_message(self.current_chat_id, content), show_user=content)

    async def _start_stream(self, stream, show_user: str | None) -> None:
        if self._generation_active:
            self.notify("A response is already in progress.", severity="warning")
            return
        if show_user is not None:
            await self._append_message(show_user, "user")
        self._generation_active = True
        self._generation_worker = self.run_worker(
            self._render_stream(stream), group="generation", exclusive=True
        )

    async def _render_stream(self, stream) -> None:
        prompt = self.query_one("#prompt", Input)
        prompt.disabled = True
        content = ""
        self._streamed_content = ""
        self._streaming_message = await self._append_message("", "assistant")
        try:
            async for message in stream:
                if isinstance(message, AIMessageChunk):
                    content += _content_text(message.content)
                    self._streamed_content = content
                    await self._streaming_message.update(content)
                elif isinstance(message, AIMessage):
                    await self._streaming_message.update(_content_text(message.content))
        except asyncio.CancelledError:
            await self._streaming_message.update(f"{content}\n\n[Generation cancelled]")
            raise
        except Exception as error:
            await self._streaming_message.update(f"{content}\n\n[Error: {error}]")
        finally:
            self._streaming_message = None
            self._generation_active = False
            prompt.disabled = False
            prompt.focus()

    async def _open_picker(self) -> None:
        self._picker_chats = await self.service.list_chats()
        picker = self.query_one("#picker", ListView)
        await picker.clear()
        for chat in self._picker_chats:
            await picker.append(ListItem(Static(chat.title or "(untitled)")))
        self.query_one("#transcript", VerticalScroll).display = False
        picker.display = True
        picker.focus()
        if not self._picker_chats:
            self.notify("No chats yet.")

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not self._is_picker_open() or event.list_view.index is None:
            return
        chat = self._picker_chats[event.list_view.index]
        self.current_chat_id = chat.id
        self._close_picker()
        await self._render_history(chat.id)
        self.notify("Resumed chat.")

    def action_escape(self) -> None:
        if self._is_picker_open():
            self._close_picker()

    def action_interrupt(self) -> None:
        if self._generation_active:
            self._generation_worker.cancel()
        else:
            self.exit()

    def _close_picker(self) -> None:
        self.query_one("#picker", ListView).display = False
        self.query_one("#transcript", VerticalScroll).display = True
        self.query_one("#prompt", Input).focus()

    def _is_picker_open(self) -> bool:
        return self.query_one("#picker", ListView).display

    async def _render_history(self, chat_id: UUID) -> None:
        await self._clear_transcript()
        for message in await self.service.get_messages(chat_id):
            if isinstance(message, HumanMessage):
                await self._append_message(_content_text(message.content), "user")
            elif isinstance(message, AIMessage):
                await self._append_message(_content_text(message.content), "assistant")

    async def _clear_transcript(self) -> None:
        await self.query_one("#transcript", VerticalScroll).remove_children()

    async def _append_message(self, content: str, style: str) -> Markdown:
        message = Markdown(content, classes=f"message {style}")
        transcript = self.query_one("#transcript", VerticalScroll)
        await transcript.mount(message)
        transcript.scroll_end(animate=False)
        return message

    async def _show_help(self) -> None:
        await self._append_message(HELP, "assistant")


def _content_text(content: str | list[str | dict]) -> str:
    return content if isinstance(content, str) else str(content)
