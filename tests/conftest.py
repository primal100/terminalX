import pytest
import getpass
from terminalX.connections import Client
from terminalX.x11 import terminate_x11_servers


@pytest.fixture(scope="session")
def ssh_host() -> str:
    return '127.0.0.1'


@pytest.fixture(scope="session")
def ssh_port() -> int:
    return 22


@pytest.fixture(scope="session")
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
    terminate_x11_servers()


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


@pytest.fixture(scope="session")
def next_hop() -> str:
    return '172.31.62.223'


@pytest.fixture
def next_hop_port() -> int:
    return 22


@pytest.fixture
def tunnel_port() -> int:
    return 8888


@pytest.fixture
def ssh_client_with_src_tunnel(ssh_host, ssh_port, username, tunnel_port, next_hop, next_hop_port) -> Client:
    client = Client(ssh_host, port=ssh_port, username=username, timeout=5, term='linux',
                    tunnels=[{'src': ('127.0.0.1', tunnel_port), 'dst': (next_hop, next_hop_port)}])
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
def ssh_client_via_socks(ssh_host, ssh_port, socks_port, username, next_hop, next_hop_port) -> Client:
    client = Client(next_hop, port=next_hop_port, username=username, timeout=10, x11=False, term='linux',
                    proxy_host=ssh_host, proxy_port=socks_port, proxy_version="socks5")
    yield client
    client.close()


@pytest.fixture
def proxy_command(ssh_host, username, ssh_port, next_hop, next_hop_port) -> str:
    return f"ssh -o StrictHostKeyChecking=no -l {username} {ssh_host} -p {ssh_port} nc {next_hop} {next_hop_port}"


@pytest.fixture
def ssh_client_via_proxy_command(next_hop, next_hop_port, proxy_command, username) -> Client:
    client = Client(next_hop, port=next_hop_port, username=username, timeout=10, x11=False, term='linux',
                    proxy_command=proxy_command)
    yield client
    client.close()


@pytest.fixture
def ssh_client_via_jump_server(ssh_host, ssh_port, username, next_hop, next_hop_port) -> Client:
    client = Client(next_hop, port=next_hop_port, username=username, timeout=10, x11=False, term='linux',
                    jump_hosts=[{'host': ssh_host, 'port': ssh_port, 'username': username, 'key_filename': None}])
    yield client
    client.close()
