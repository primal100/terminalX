from terminalX.utils import parse_string_placeholders


def test_proxy_command_placeholder_substitution(proxy_command):
    assert parse_string_placeholders(proxy_command, "127.0.0.1", 22) == f"ncat 127.0.0.1 22"
