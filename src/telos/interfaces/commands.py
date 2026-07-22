"""Presentation-neutral slash-command parsing."""

from dataclasses import dataclass
from enum import StrEnum


class CommandName(StrEnum):
    HELP = "help"
    NEW = "new"
    RESUME = "resume"
    RETRY = "retry"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Command:
    name: CommandName
    argument: str = ""


class CommandParser:
    """Map terminal input to commands without coupling to a UI."""

    _commands = {
        "/help": CommandName.HELP,
        "/new": CommandName.NEW,
        "/resume": CommandName.RESUME,
        "/chats": CommandName.RESUME,
        "/retry": CommandName.RETRY,
    }

    def parse(self, text: str) -> Command | None:
        command, _, argument = text.partition(" ")
        name = self._commands.get(command)
        if name is not None:
            return Command(name, argument.strip())
        if text.startswith("/"):
            return Command(CommandName.UNKNOWN, command)
        return None
