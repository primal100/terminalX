import time


def test_ssh_connection(ssh_client):
    ssh_client.connect()
    assert ssh_client.transport


def test_ssh_terminal(ssh_client_connected):
    ssh_client_connected.invoke_shell()
    screen = ssh_client_connected.display_screen()
    assert screen
    ssh_client_connected.send('echo Hello World')
    time.sleep(0.2)
    screen = ssh_client_connected.display_screen()
    assert "echo Hello World" in screen[-1]
    ssh_client_connected.send('\n')
    time.sleep(0.2)
    screen = ssh_client_connected.display_screen()
    assert screen[-2].startswith('Hello World')


def test_ssh_terminal_file_editing(ssh_client_with_shell):
    screen = ssh_client_with_shell.display_screen()
    assert screen
    file_to_create = "/tmp/test.txt"
    swap_file = "/tmp/.test.txt.swp"
    ssh_client_with_shell.send(f'rm -f {file_to_create} {swap_file}\n')
    ssh_client_with_shell.send(f'vi {file_to_create}\n')
    time.sleep(1)
    screen = ssh_client_with_shell.display_screen()
    assert file_to_create in screen[-1]
    assert ssh_client_with_shell.cursors() == (0, 0)
    ssh_client_with_shell.send('i')
    time.sleep(0.2)
    screen = ssh_client_with_shell.display_screen()
    assert "INSERT" in screen[-1]
    ssh_client_with_shell.send('Hello World')
    time.sleep(0.2)
    assert ssh_client_with_shell.cursors() == (11, 0)
    screen = ssh_client_with_shell.display_screen()
    assert "Hello World" in screen[0]

    for i in range(0, 5):
        ssh_client_with_shell.send(chr(0x1b)+"[D")
    time.sleep(0.2)
    assert ssh_client_with_shell.cursors() == (6, 0)

    ssh_client_with_shell.send(chr(0x1b)+"[3~")
    ssh_client_with_shell.send('w')
    ssh_client_with_shell.send('\x1B')
    time.sleep(0.3)
    screen = ssh_client_with_shell.display_screen()
    assert "Hello world" in screen[0]
    assert "INSERT" not in screen[-1]
    assert ssh_client_with_shell.cursors() == (6, 0)
    ssh_client_with_shell.send(':wq!\n')
    time.sleep(0.3)
    ssh_client_with_shell.send(f'more {file_to_create}\n')
    time.sleep(0.3)
    screen = ssh_client_with_shell.display_screen()
    assert "Hello world" in screen[-2]


def test_ssh_tunnelling(ssh_client_with_src_tunnel_connected, ssh_client_via_tunnel):
    ssh_client_via_tunnel.connect()
    ssh_client_via_tunnel.invoke_shell()
    ssh_client_via_tunnel.send('echo Hello World')
    time.sleep(0.2)
    ssh_client_via_tunnel.send('\n')
    time.sleep(0.2)
    screen = ssh_client_via_tunnel.display_screen()
    assert screen[-2].startswith('Hello World')
    ssh_client_via_tunnel.close()


def test_socks_proxy(ssh_client_with_socks_tunnel_connected, ssh_client_via_socks):
    ssh_client_via_socks.connect()
    ssh_client_via_socks.invoke_shell()
    ssh_client_via_socks.send('echo Hello World')
    time.sleep(0.3)
    ssh_client_via_socks.send('\n')
    time.sleep(1)
    screen = ssh_client_via_socks.display_screen()
    assert screen[-2].startswith('Hello World')
    time.sleep(20)
    ssh_client_via_socks.close()

