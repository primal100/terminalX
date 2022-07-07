from terminalX.forwarder import forward_tunnel
import time


def test_forward_server(ssh_client_connected, tunnel_port, tunnel_to, ssh_port, ssh_client_via_tunnel):
    server = forward_tunnel(tunnel_port, tunnel_to, ssh_port, ssh_client_connected.transport, "127.0.0.1")
    server.wait_started(5)
    ssh_client_via_tunnel.connect()
    ssh_client_via_tunnel.invoke_shell()
    ssh_client_via_tunnel.send('echo Hello World')
    time.sleep(0.1)
    ssh_client_via_tunnel.send('\n')
    time.sleep(0.2)
    screen = ssh_client_via_tunnel.display_screen()
    assert screen[-2].startswith('Hello World')
    ssh_client_via_tunnel.close()
    server.shutdown()
