#!/usr/bin/env python
# With thanks to https://stackoverflow.com/questions/12354047/x11-forwarding-with-paramiko dnozay answer


import threading
from functools import partial
import socket
import selectors
import logging
import paramiko

LOGGER = logging.getLogger(__name__)

x11_server = ('127.0.0.1', 6000)


class X11ServerConnectionFailure(BaseException):
    message = "Unable to connect to local X11 Server. Please ensure an X11 server such as VcXsrv or xming is running"


def connect_to_x11_server() -> socket.socket:
    local_x11_socket = socket.socket()
    try:
        local_x11_socket.connect(('127.0.0.1', 6000))
    except socket.error:
        raise X11ServerConnectionFailure
    return local_x11_socket


def x11_handler(channels: dict[int, tuple], selector: selectors.BaseSelector,
                channel: paramiko.Channel, address: tuple[str, int]):
    '''handler for incoming x11 connections
    for each x11 incoming connection,
    - get a connection to the local display
    - maintain bidirectional map of remote x11 channel to local x11 channel
    - add the descriptors to the poller
    - queue the channel (use transport.accept())'''
    x11_chanfd = channel.fileno()
    local_x11_socket = connect_to_x11_server()
    local_x11_socket_fileno = local_x11_socket.fileno()
    channels[x11_chanfd] = channel, local_x11_socket
    channels[local_x11_socket_fileno] = local_x11_socket, channel
    selector.register(x11_chanfd, selectors.EVENT_READ)
    selector.register(local_x11_socket_fileno, selectors.EVENT_READ)
    transport = channel.get_transport()
    transport._queue_incoming_channel(channel)


def process_x11(session, channels: dict[int, tuple], selector: selectors.BaseSelector):
    # accept first remote x11 connection
    transport = session.get_transport()
    transport.accept()

    # event loop
    while not session.exit_status_ready():
        for key, mask in selector.select():
            fileObj, fd, events, data = key
            # accept subsequent x11 connections if any
            if len(transport.server_accepts) > 0:
                transport.accept()
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


def register_x11(session: paramiko.Channel, screen_number: int = None, auth_protocol: str = None):
    selector = selectors.DefaultSelector()
    channels = {}
    handler = partial(x11_handler, channels, selector)
    session.request_x11(handler=handler, screen_number=screen_number, auth_protocol=auth_protocol)
    thread = threading.Thread(target=process_x11, args=(session, channels, selector))
    thread.start()
