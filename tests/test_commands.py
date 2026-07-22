from telos.interfaces.commands import CommandName, CommandParser


def test_parser_maps_supported_commands_and_message_text():
    parser = CommandParser()

    assert parser.parse("hello") is None
    assert parser.parse("/chats").name is CommandName.RESUME
    assert parser.parse("/resume 2").argument == "2"
    assert parser.parse("/wat").name is CommandName.UNKNOWN
