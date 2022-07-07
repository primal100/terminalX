import os
import socket
from pathlib import Path


def get_placeholders(remote_host: str = "", remote_port: int = 22,
                     remote_username: str = "", remote_home: str = "") -> dict[str]:
    hostname = socket.gethostname()
    return {
        '%d': str(Path.home()),
        '%h': remote_host,
        '%l': hostname,
        '%n': hostname,
        '%p': str(remote_port),
        '%r': remote_username,
        '%u': os.getlogin(),
        "%z": remote_home
    }


def parse_string_placeholders(text: str, remote_host: str = "", remote_port: int = 22,
                              remote_username: str = "", remote_home: str = "") -> str:
    for k, v in get_placeholders(remote_host, remote_port, remote_username, remote_home).items():
        text = text.replace(k, v)
    return text


def static(**kwargs):
    """
    # https://stackoverflow.com/questions/279561/what-is-the-python-equivalent-of-static-variables-inside-a-function
    To allow static variables in a function
    :param kwargs: static variables and initial value
    :return: The function
    """
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate
