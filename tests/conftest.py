import pytest
import getpass
import time
from terminalX.connections import Client


@pytest.fixture
def ssh_host() -> str:
    return '192.168.1.29'


@pytest.fixture
def ssh_port() -> int:
    return 22


@pytest.fixture
def username() -> str:
    return getpass.getuser()


@pytest.fixture
def ssh_client(ssh_host, ssh_port, username) -> Client:
    client = Client(ssh_host, port=ssh_port, username=username, timeout=10, x11=False, term='linux')
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


@pytest.fixture
def tunnel_to() -> str:
    return '192.168.1.29'


@pytest.fixture
def tunnel_port() -> int:
    return 8888


@pytest.fixture
def ssh_client_with_src_tunnel(ssh_host, ssh_port, username, tunnel_port, tunnel_to) -> Client:
    client = Client(ssh_host, port=ssh_port, username=username, timeout=5, term='linux',
                    tunnels=[{'src': ('127.0.0.1', tunnel_port), 'dst': (tunnel_to, 22)}])
    yield client
    client.close()


@pytest.fixture
def ssh_client_with_src_tunnel_connected(ssh_client_with_src_tunnel) -> Client:
    ssh_client_with_src_tunnel.connect()
    ssh_client_with_src_tunnel.wait_started()
    yield ssh_client_with_src_tunnel
    ssh_client_with_src_tunnel.close()


@pytest.fixture
def ssh_client_via_tunnel(tunnel_port, username) -> Client:
    client = Client("127.0.0.1", port=tunnel_port, username=username, timeout=10, x11=False, term='linux')
    yield client
    client.close()


@pytest.fixture
def socks_port() -> int:
    return 8889


@pytest.fixture
def ssh_client_with_socks_tunnel(ssh_host, ssh_port, username, socks_port) -> Client:
    client = Client(ssh_host, port=ssh_port, username=username, timeout=5, x11=False, term='linux',
                    socks_tunnels=[('127.0.0.1', socks_port)])
    yield client
    client.close()


@pytest.fixture
def ssh_client_with_socks_tunnel_connected(ssh_client_with_socks_tunnel) -> Client:
    ssh_client_with_socks_tunnel.connect()
    ssh_client_with_socks_tunnel.wait_started()
    yield ssh_client_with_socks_tunnel
    ssh_client_with_socks_tunnel.close()


@pytest.fixture
def ssh_client_via_socks(ssh_host, ssh_port, socks_port, username) -> Client:
    client = Client(ssh_host, port=ssh_port, username=username, timeout=10, x11=False, term='linux',
                    proxy_host='127.0.0.1', proxy_port=socks_port, proxy_version="socks5")
    yield client
    client.close()

