import re
import time

import pytest


def test_ssh_connection_full_name(ssh_client, ssh_host, username):
    assert ssh_client.full_name() == f'{ssh_host} ({username})'


def test_ssh_connection(ssh_client):
    ssh_client.connect()
    assert ssh_client.transport and ssh_client.transport.is_active() and ssh_client.transport.is_authenticated()


def find_terminal_lines(display: list[str]) -> list[str]:
    return [line for line in display if re.search('[a-zA-Z]', line)]


def test_ssh_terminal(ssh_client_connected):
    ssh_client_connected.invoke_shell()
    time.sleep(2)
    screen = ssh_client_connected.display_screen()
    assert screen
    line_changes = ssh_client_connected.display_screen_line_changes()
    assert len(line_changes) == len(screen)
    ssh_client_connected.send('echo Hello World')
    time.sleep(2)
    screen = ssh_client_connected.display_screen()
    terminal_lines = find_terminal_lines(screen)
    assert "echo Hello World" in terminal_lines[-1]
    line_changes = ssh_client_connected.display_screen_line_changes()
    current_line = ssh_client_connected.cursors()[0]
    assert len(line_changes) == 1
    assert "echo Hello World" in line_changes[current_line]
    ssh_client_connected.send('\n')
    time.sleep(0.3)
    screen = ssh_client_connected.display_screen()
    assert find_terminal_lines(screen)[-2].startswith('Hello World')
    line_changes = ssh_client_connected.display_screen_line_changes()
    assert len(line_changes) == 2


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
    time.sleep(0.3)
    screen = ssh_client_with_shell.display_screen()
    assert "INSERT" in find_terminal_lines(screen)[-1]
    ssh_client_with_shell.send('Hello World')
    time.sleep(0.3)
    assert ssh_client_with_shell.cursors() == (11, 0)
    screen = find_terminal_lines(ssh_client_with_shell.display_screen())
    assert "Hello World" in screen[0]

    for i in range(0, 5):
        ssh_client_with_shell.send(chr(0x1b)+"[D")
    time.sleep(0.3)
    assert ssh_client_with_shell.cursors() == (6, 0)

    ssh_client_with_shell.send(chr(0x1b)+"[3~")
    ssh_client_with_shell.send('w')
    ssh_client_with_shell.send('\x1B')
    time.sleep(0.3)
    screen = find_terminal_lines(ssh_client_with_shell.display_screen())
    assert "Hello world" in screen[0]
    assert "INSERT" not in screen[-1]
    assert ssh_client_with_shell.cursors() == (6, 0)
    ssh_client_with_shell.send(':wq!\n')
    time.sleep(0.3)
    ssh_client_with_shell.send(f'more {file_to_create}\n')
    time.sleep(0.3)
    screen = find_terminal_lines(ssh_client_with_shell.display_screen())
    assert "Hello world" in screen[-2]


def test_ssh_tunnelling(ssh_client_with_src_tunnel_connected, ssh_client_via_tunnel):
    ssh_client_via_tunnel.connect()
    ssh_client_via_tunnel.invoke_shell()
    ssh_client_via_tunnel.send('echo Hello World')
    time.sleep(0.3)
    ssh_client_via_tunnel.send('\n')
    time.sleep(0.3)
    screen = find_terminal_lines(ssh_client_via_tunnel.display_screen())
    assert screen[-2].startswith('Hello World')
    ssh_client_via_tunnel.close()


def test_socks_proxy(ssh_client_with_socks_tunnel_connected, ssh_client_via_socks):
    ssh_client_via_socks.connect()
    ssh_client_via_socks.invoke_shell()
    ssh_client_via_socks.send('echo Hello World')
    time.sleep(0.3)
    ssh_client_via_socks.send('\n')
    time.sleep(1)
    screen = find_terminal_lines(ssh_client_via_socks.display_screen())
    assert screen[-2].startswith('Hello World')
    ssh_client_via_socks.close()


@pytest.mark.skip("Not working")
def test_proxy_command(ssh_client_via_proxy_command):
    ssh_client_via_proxy_command.connect()
    ssh_client_via_proxy_command.invoke_shell()
    ssh_client_via_proxy_command.send('echo Hello World')
    time.sleep(0.3)
    ssh_client_via_proxy_command.send('\n')
    time.sleep(1)
    screen = find_terminal_lines(ssh_client_via_proxy_command.display_screen())
    assert screen[-2].startswith('Hello World')
    ssh_client_via_proxy_command.close()


def test_ssh_jump_server(ssh_client_via_jump_server):
    ssh_client_via_jump_server.connect()
    ssh_client_via_jump_server.invoke_shell()
    ssh_client_via_jump_server.send('echo Hello World')
    time.sleep(0.3)
    ssh_client_via_jump_server.send('\n')
    time.sleep(1)
    screen = find_terminal_lines(ssh_client_via_jump_server.display_screen())
    assert screen[-2].startswith('Hello World')
    ssh_client_via_jump_server.close()


def test_ssh_x11(ssh_client_x11):
    ssh_client_x11.connect()
    ssh_client_x11.invoke_shell()
    screen = ssh_client_x11.display_screen()
    assert screen
    ssh_client_x11.send('echo $DISPLAY\n')
    time.sleep(0.3)
    screen = ssh_client_x11.display_screen()
    assert "echo $DISPLAY" in find_terminal_lines(screen)[-3]
    assert find_terminal_lines(screen)[-2].startswith('localhost:')
    ssh_client_x11.send('xterm\n')
    print('xterm window should appear now')
    time.sleep(20)
