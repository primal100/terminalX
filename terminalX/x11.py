#!/usr/bin/env python
# With thanks to https://stackoverflow.com/questions/12354047/x11-forwarding-with-paramiko dnozay answer


import os
import select
import sys
import socket
import logging
import Xlib.support.connect as xlib_connect
import paramiko

LOGGER = logging.getLogger(__name__)


# maintain map
# { fd: (channel, remote channel), ... }
channels = {}

poller = select.poll()

def x11_handler(channel: paramiko.Channel, address: tuple[str, int]):
    '''handler for incoming x11 connections
    for each x11 incoming connection,
    - get a connection to the local display
    - maintain bidirectional map of remote x11 channel to local x11 channel
    - add the descriptors to the poller
    - queue the channel (use transport.accept())'''
    local_x11_display = xlib_connect.get_display(os.environ['DISPLAY'])
    x11_chanfd = channel.fileno()
    local_x11_socket = xlib_connect.get_socket(*local_x11_display[:3])
    local_x11_socket_fileno = local_x11_socket.fileno()
    channels[x11_chanfd] = channel, local_x11_socket
    channels[local_x11_socket_fileno] = local_x11_socket, channel
    poller.register(x11_chanfd, select.POLLIN)
    poller.register(local_x11_socket, select.POLLIN)
    LOGGER.debug('x11 channel on: %s %s', src_addr, src_port)
    transport._queue_incoming_channel(channel)

def flush_out(session):
    while session.recv_ready():
        sys.stdout.write(session.recv(4096))
    while session.recv_stderr_ready():
        sys.stderr.write(session.recv_stderr(4096))


def register_x11(session: paramiko.Channel):
    # start x11 session
    session.request_x11(handler=x11_handler)
    session.exec_command('xterm')
    session_fileno = session.fileno()
    poller.register(session_fileno, select.POLLIN)
    # accept first remote x11 connection
    transport = session.get_transport()
    transport.accept()

    # event loop
    while not session.exit_status_ready():
        poll = poller.poll()
        # accept subsequent x11 connections if any
        if len(transport.server_accepts) > 0:
            transport.accept()
        if not poll: # this should not happen, as we don't have a timeout.
            break
        for fd, event in poll:
            if fd == session_fileno:
                flush_out(session)
            # data either on local/remote x11 socket
            if fd in channels.keys():
                channel, counterpart = channels[fd]
                try:
                    # forward data between local/remote x11 socket.
                    data = channel.recv(4096)
                    counterpart.sendall(data)
                except socket.error:
                    channel.close()
                    counterpart.close()
                    del channels[fd]

    print('Exit status:', session.recv_exit_status())
    flush_out(session)
    session.close()
