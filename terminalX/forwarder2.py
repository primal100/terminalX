#!/usr/bin/env python

# Copyright (C) 2003-2007  Robey Pointer <robeypointer@gmail.com>
#
# This file is part of paramiko.
#
# Paramiko is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# Paramiko is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Paramiko; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA.


# Inspired by https://raw.githubusercontent.com/paramiko/paramiko/main/demos/forward.py

from functools import partial
import select
import socketserver
import threading


import paramiko

SSH_PORT = 22
DEFAULT_PORT = 4000

g_verbose = True


class TunnelNotStartedException(BaseException):
    pass


class ForwardServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ready_event = threading.Event()
        print('Created forward server')

    def service_actions(self):
        self.ready_event.set()

    def wait_started(self, timeout: int = None):
        if not self.ready_event.wait(timeout=timeout):
            raise TunnelNotStartedException(
                f'Could not start tunnel on {":".join(str(i) for i in self.server_address)} after {timeout} seconds')


class Handler(socketserver.BaseRequestHandler):

    def __init__(self, chain_host: str, chain_port: int, ssh_transport: paramiko.Transport, request, client_address: str, server: ForwardServer):
        print('Running __init__', chain_host)
        self.chain_host = chain_host
        self.chain_port = chain_port
        self.ssh_transport = ssh_transport
        print('initiating handler', self.chain_host)
        super().__init__(request, client_address, server)

    def handle(self):
        print('handling tunnel request')
        try:
            chan = self.ssh_transport.open_channel(
                "direct-tcpip",
                (self.chain_host, self.chain_port),
                self.request.getpeername(),
            )
        except Exception as e:
            verbose(
                "Incoming request to %s:%d failed: %s"
                % (self.chain_host, self.chain_port, repr(e))
            )
            return
        if chan is None:
            verbose(
                "Incoming request to %s:%d was rejected by the SSH server."
                % (self.chain_host, self.chain_port)
            )
            return

        verbose(
            "Connected!  Tunnel open %r -> %r -> %r"
            % (
                self.request.getpeername(),
                chan.getpeername(),
                (self.chain_host, self.chain_port),
            )
        )

        recv_chan_thread = threading.Thread(target=self.recv_on_tunnel, args=(chan,))
        recv_chan_thread.start()

        while True:
            r, w, x = select.select([self.request, chan], [], [])
            if self.request in r:
                data = self.request.recv(1024)
                if len(data) == 0:
                    break
                print('sending data to channel')
                chan.send(data)

        peername = self.request.getpeername()
        chan.close()
        self.request.close()
        verbose("Tunnel closed from %r" % (peername,))

    def recv_on_tunnel(self, chan: paramiko.Channel):
        print('running recv_on_tunnel')
        while True:
            data = chan.recv(1024)
            if len(data) == 0:
                break
            print('sending data to putty')
            self.request.send(data)


def create_forward_server(local_port: int, remote_host: str, remote_port: int, transport: paramiko.Transport,
                          local_host: str = "") -> ForwardServer:
    return ForwardServer((local_host, local_port), partial(Handler, remote_host, remote_port, transport))


def forward_tunnel(local_port: int, remote_host: str, remote_port: int, transport: paramiko.Transport,
                   local_host: str = "") -> ForwardServer:
    server = create_forward_server(local_port, remote_host, remote_port, transport, local_host)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def verbose(s):
    if g_verbose:
        print(s)

