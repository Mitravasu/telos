"""Minimal terminal interface."""

from uuid import UUID


HELP = "Commands: /new, /chats, /resume [number], /retry, /help. Ctrl+C or Ctrl+D exits."


class CLI:
    def __init__(self, service, input_fn=input, output_fn=print) -> None:
        self.service = service
        self.input = input_fn
        self.output = output_fn
        self.current_chat_id: UUID | None = None
        self.last_listed_chats = []

    def run(self) -> None:
        self.output("Telos. " + HELP)
        while True:
            try:
                line = self.input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                self.output("\nGoodbye.")
                return
            if line:
                self.handle(line)

    def handle(self, line: str) -> None:
        if line.startswith("/"):
            self._command(line)
            return
        if self.current_chat_id is None:
            self.current_chat_id = self.service.create_chat().id
        try:
            self.output(self.service.send_message(self.current_chat_id, line).content)
        except Exception as error:
            self.output(f"Error: {error}")

    def _command(self, line: str) -> None:
        command, _, argument = line.partition(" ")
        if command == "/new":
            self.current_chat_id = None
            self.output("A new chat will start with your next message.")
        elif command == "/chats":
            self.last_listed_chats = self.service.list_chats()
            for index, chat in enumerate(self.last_listed_chats, 1):
                self.output(f"{index}. {chat.title or '(untitled)'} [{chat.id}]")
        elif command == "/resume":
            if not argument:
                self._command("/chats")
            elif argument.isdigit() and 1 <= int(argument) <= len(self.last_listed_chats):
                self.current_chat_id = self.last_listed_chats[int(argument) - 1].id
                self.output("Resumed chat.")
            else:
                self.output("Run /chats, then use /resume <number>.")
        elif command == "/retry":
            if self.current_chat_id is None:
                self.output("No current chat to retry.")
            else:
                try:
                    self.output(self.service.retry(self.current_chat_id).content)
                except Exception as error:
                    self.output(f"Error: {error}")
        elif command == "/help":
            self.output(HELP)
        else:
            self.output("Unknown command. " + HELP)
