import asyncio

from telos.observability import TelosCallbackHandler


def test_cancelled_generation_is_not_reported_as_an_error():
    handler = object.__new__(TelosCallbackHandler)

    assert handler._get_error_level_and_status_message(asyncio.CancelledError()) == (
        "DEFAULT",
        "Generation interrupted",
    )


def test_non_cancellation_errors_keep_langfuses_default_classification():
    handler = object.__new__(TelosCallbackHandler)

    assert handler._get_error_level_and_status_message(ValueError("provider down")) == (
        "ERROR",
        "provider down",
    )
