"""Prompt construction for the root career agent."""

from langchain_core.messages import BaseMessage, SystemMessage

SYSTEM_PROMPT = """You are Telos, a thoughtful career agent. Help the user make practical progress
in their career. Be candid, specific, and ask focused questions when context is missing."""


def build_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    return [SystemMessage(content=SYSTEM_PROMPT), *messages]
