#!/usr/bin/env python
# With thanks to https://stackoverflow.com/questions/12354047/x11-forwarding-with-paramiko dnozay answer

import os
import threading
from .executors import executor
from functools import partial
import socket
import selectors
import logging
import paramiko
import subprocess

logger = logging.getLogger(__name__)


if os.name == "nt" or not hasattr(socket, 'AF_UNIX'):
    x11_server = ('127.0.0.1', 6000)
    x11_family = socket.AF_INET
else:
    x11_server = '/tmp/.X11-unix/X0'
    x11_family = socket.AF_UNIX


class X11ServerConnectionFailure(BaseException):
    message = "Unable to connect to local X11 Server. Please ensure an X11 server such as VcXsrv or xming is running. "

    def __init__(self, error: str):
        self.message += error


potential_x11_servers: dict[str, tuple[list[str], list[str]]]

if os.name == "nt":
    potential_x11_servers = {
        'xming': ([
            "C:\\Program Files (x86)\\Xming\\Xming.exe"], [":0", "-clipboard", "-multiwindow"]),
        'VcXsrv': ([
            "C:\\Program Files\\VcXsrv\\vcxsrv.exe"
        ], []),
    }
else:
    potential_x11_servers = {}


x11_server_processes: list[subprocess.Popen] = []


def terminate_x11_servers():
    for p in x11_server_processes:
        p.terminate()


def start_x11_server() -> bool:
    path = None
    args = []
    for k, v in potential_x11_servers.items():
        path, args = v
        where = 'where' if os.name == 'nt' else 'which'
        if subprocess.run([where, k]).returncode == 0:
            path = k            # X Server Application is in Windows Path
            break
        else:
            try:
                path = next(filter(os.path.exists, path))
                break
            except StopIteration:
                continue
    if path:
        args = [path] + args
        x11_server_processes.append(subprocess.Popen(args))
        return True
    return False


def connect_to_x11_server(x11_try_start_server: bool = False) -> socket.socket:
    local_x11_socket = socket.socket(family=x11_family)
    for i in range(0, 2):
        try:
            logger.debug('Connecting to X11 server %s', x11_server)
            local_x11_socket.connect(x11_server)
            break
        except socket.error as e:
            if i == 0 and x11_try_start_server:
                if not start_x11_server():
                    raise X11ServerConnectionFailure(str(e))
            else:
                raise X11ServerConnectionFailure
    return local_x11_socket


def _x11_handler(channels: dict[int, tuple], selector: selectors.BaseSelector, x11_try_start_server: bool,
                channel: paramiko.Channel, address: tuple[str, int]):
    '''handler for incoming x11 connections
    for each x11 incoming connection,
    - get a connection to the local display
    - maintain bidirectional map of remote x11 channel to local x11 channel
    - add the descriptors to the poller
    - queue the channel (use transport.accept())'''
    x11_chanfd = channel.fileno()
    local_x11_socket = connect_to_x11_server(x11_try_start_server)
    local_x11_socket_fileno = local_x11_socket.fileno()
    channels[x11_chanfd] = channel, local_x11_socket
    channels[local_x11_socket_fileno] = local_x11_socket, channel
    selector.register(channel, selectors.EVENT_READ)
    selector.register(local_x11_socket, selectors.EVENT_READ)
    transport = channel.get_transport()
    transport._queue_incoming_channel(channel)


def x11_handler(channels: dict[int, tuple], selector: selectors.BaseSelector, x11_try_start_server: bool,
                channel: paramiko.Channel, address: tuple[str, int]):
    """
    Run in thread so as not to block terminal while connectiing to x11 server
    """
    logger.info('Running X11 handler')
    executor.submit(_x11_handler, channels, selector, x11_try_start_server, channel, address)


def process_x11(session, channels: dict[int, tuple], selector: selectors.BaseSelector):
    # accept first remote x11 connection
    transport = session.get_transport()

    while not session.exit_status_ready():
        if not bool(selector.get_map()):    # Select will fail in Windows if no sockets are registered
            transport.accept(timeout=0.25)
        else:
            for key, mask in selector.select(timeout=0.5):
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
                        selector.unregister(channel)
                        selector.unregister(counterpart)


def register_x11(session: paramiko.Channel, screen_number: int = None, auth_protocol: str = None,
                 x11_try_start_server: bool = False) -> threading.Thread:
    selector = selectors.DefaultSelector()
    channels = {}
    handler = partial(x11_handler, channels, selector, x11_try_start_server)
    session.request_x11(handler=handler, screen_number=screen_number, auth_protocol=auth_protocol)
    thread = threading.Thread(target=process_x11, args=(session, channels, selector))
    thread.start()
    return thread
