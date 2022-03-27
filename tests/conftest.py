import pytest
import getpass
from terminalX.connections import Client


@pytest.fixture
def ssh_host() -> str:
    return 'localhost'


@pytest.fixture
def ssh_port() -> int:
    return 22


@pytest.fixture
def username() -> str:
    return getpass.getuser()


@pytest.fixture
def ssh_client(ssh_host, ssh_port, username) -> Client:
    client = Client(ssh_host, port=ssh_port, username=username, timeout=5, x11=False, term='linux')
    yield client
    client.close()


@pytest.fixture
def ssh_client_x11(ssh_host, ssh_port, username) -> Client:
    client = Client(ssh_host, port=ssh_port, username=username, timeout=5, x11=True, term='linux')
    yield client
    client.close()


@pytest.fixture
def ssh_client_connected(ssh_client) -> Client:
    ssh_client.connect()
    yield ssh_client
    ssh_client.close()


@pytest.fixture
def ssh_client_x11_connected(ssh_client_x11) -> Client:
    ssh_client_x11.connect()
    yield ssh_client_x11
    ssh_client_x11.close()


@pytest.fixture
def ssh_client_with_shell(ssh_client_connected) -> Client:
    ssh_client_connected.invoke_shell()
    yield ssh_client_connected
    ssh_client_connected.close()


@pytest.fixture
def ssh_client_x11_with_shell(ssh_client_x11_connected) -> Client:
    ssh_client_x11_connected.invoke_shell()
    yield ssh_client_x11_connected
    ssh_client_x11_connected.close()
