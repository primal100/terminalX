#!/usr/bin/env python

"""
For testing purposes.
Taken from https://gist.githubusercontent.com/cschwede/3e2c025408ab4af531651098331cce45/raw/6fe794b0dff3e02a58a20fd6911e533be9d15d07/sample_ssh_server.py
"""


import getpass
import os
import socket
import sys
import threading

import paramiko
from typing import Callable
from .hashing import verify_hash
from .types import File, StringDict


class InMemoryPasswordClientHandler(paramiko.ServerInterface):
    def __init__(self, host_key: paramiko.PKey, passwords: StringDict):
        self.event = threading.Event()
        self.host_key = host_key
        self.passwords = passwords

    def check_channel_request(self, kind: str, chanid: int):
        print('checking channel request', kind, chanid)
        if kind == 'session':
            return paramiko.common.OPEN_SUCCEEDED

    def check_channel_pty_request(self, channel: paramiko.Channel, term: str, width: int, height: int, pixelwidth: int, pixelheight: int, modes: bytes):
        print('checking channel_pty request', term, width, height, pixelwidth, pixelheight, modes)
        return True

    def check_channel_shell_request(self, channel: paramiko.Channel):
        print('check channel shell request')
        channel.exec_command("cmd")
        return True

    def check_auth_password(self, username: str, password: str):
        if os.name == 'nt':
            username = username.split('\\')[-1]      # Remove domain part
        password_hash = self.passwords.get(username)
        if password_hash and verify_hash(password, password_hash):
            return paramiko.common.AUTH_SUCCESSFUL
        return paramiko.common.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        if username not in self.passwords:
            return paramiko.common.AUTH_FAILED
        return paramiko.common.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username: str):
        return 'password,publickey'

    def check_channel_exec_request(self, channel: paramiko.Channel, command: str):
        print('checking channel exec request', channel, command)
        return True


class Listener:
    actual_host: str = None
    actual_port: int = None
    client_handler: paramiko.ServerInterface = InMemoryPasswordClientHandler

    def __init__(self, host_key_file: File, passwords: StringDict, host: str = '', port: int = 0):
        self.host_key = paramiko.RSAKey(filename=host_key_file)
        self.host = host
        self.port = port
        self.passwords = passwords
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(0.5)   # So keyboard interrupt works

    def on_new_client(self, client, address):
        transport = paramiko.Transport(client)
        transport.set_gss_host(socket.getfqdn(""))
        transport.load_server_moduli()
        transport.add_server_key(self.host_key)
        server = self.client_handler(self.host_key, self.passwords)
        transport.start_server(server=server)

    def listen(self, callback: Callable = None):
        self.sock.bind((self.host, self.port))
        self.host, self.port = self.sock.getsockname()
        self.sock.listen(100)
        if callback:
            callback(self.host, self.port)
        while True:
            try:
                client, address = self.sock.accept()
                thread = threading.Thread(target=self.on_new_client, args=(client, address))
                thread.start()
            except KeyboardInterrupt:
                self.close()
                break
            except socket.timeout:
                continue
            except OSError:
                break

    def listen_in_thread(self):
        thread = threading.Thread(target=self.listen, daemon=True)
        thread.start()

    def close(self):
        self.sock.close()


def print_listening_on(host: str, port: int):
    print(f'SSH server listening on {host}:{port}')


if __name__ == '__main__':
    key_file = sys.argv[1]
    if len(sys.argv) > 2:
        port = sys.argv[2]
    else:
        port = 2222
    passwords = \
        {getpass.getuser(): 'wPLL4YwL30TbZfoCvpvKc8AZM1Xp4MEX/qZNGmi6Ck9n8OGUPfZSVVusve2Cbkxq56pJuFUwSKL3fMQ0OQ3XQQ==',   # 'abcd1234'
         'testuser': 'zhtmqhZnDHQiRoSUyRoOqY8FNqgR8o0vO1STccE8lXOOKWXHkiJmrSD7KzzAZhvaFuaZ51UFcs4mG2uwFwvrOw=='}    # 'q1w2e3r4'
    ssh_server = Listener(key_file, passwords, port=port)
    ssh_server.listen(print_listening_on)

