"""Telos-specific Langfuse observation semantics."""

import asyncio

from langfuse.langchain import CallbackHandler


class TelosCallbackHandler(CallbackHandler):
    """Classify user-requested generation cancellation as expected control flow."""

    def _get_error_level_and_status_message(self, error: BaseException):
        if isinstance(error, asyncio.CancelledError):
            return "DEFAULT", "Generation interrupted"
        return super()._get_error_level_and_status_message(error)
