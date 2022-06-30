import getpass
import socket

import paramiko
import pyte
from dataclasses import dataclass, field, replace
from python_socks.sync import Proxy, ProxyType
import logging
import threading
import time

from .client import SSHClient
from .forwarder import forward_tunnel, ForwardServer
from .proxy_command import ProxyCommand
from .types import DisabledAlgorithms, StringDict, File, KnownHostsPolicy, ProxyJump, ProxyJumpPasswords, ProxyVersion, TunnelConfig
from .x11 import register_x11
from typing import Callable, Generator, Optional


logger = logging.getLogger()


class NotConnectedException(BaseException):
    message = "SSH Client is not yet connected. Call the .connect() method first"


class NoShellException(BaseException):
    message = "SSH Client shell does not exist. Call the .invoke_shell() method first"


class ShellNotStartedException(BaseException):
    pass


class SSHConfigurationException(BaseException):
    pass


class UnknownKnownHostsPolicy(SSHConfigurationException):
    pass


class UnknownSocksVersion(SSHConfigurationException):
    pass


class NotAvailableInProxyCommandMode(SSHConfigurationException):
    def __init__(self, option: str):
        super().__init__()


@dataclass
class Client:
    host: str
    port: int = 22
    name: str = None
    username: str = field(default_factory=getpass.getuser)
    key_filename: File = None
    timeout: int = None
    allow_agent: bool = False           # True when https://github.com/paramiko/paramiko/pull/2010 is merged
    look_for_keys: bool = True,
    compress: bool = False
    gss_auth: bool = False
    gss_kex: bool = False
    gss_deleg_creds: bool = False,
    gss_host: str = None
    gss_trust_dns: bool = True
    banner_timeout: float = None
    auth_timeout: float = None
    disabled_algorithms: DisabledAlgorithms = None
    host_keys_file: File = None
    term: str = 'linux'
    environment: StringDict = None
    keepalive_interval: int = None
    x11: bool = True
    x11_screen_number: int = 0
    x11_auth_protocol: str = "MIT-MAGIC-COOKIE-1"
    x11_try_start_server: bool = True
    threads: list[threading.Thread] = field(init=False, repr=False, hash=False, compare=False, default_factory=list)
    known_hosts_policy: KnownHostsPolicy = "auto"
    jump_hosts: list[ProxyJump] = None
    sub_clients: list['Client'] = field(init=False, repr=False, compare=False, hash=False, default_factory=list)
    proxy_command: str = None
    proxy_host: str = None
    proxy_port: int = None
    proxy_username: str = None
    proxy_password: str = None
    proxy_version: ProxyVersion = "socks5"
    socks_rdns: Optional[bool] = None
    socks_tunnels: Optional[list[tuple[str, int]]] = field(default_factory=list)
    tunnels: Optional[list[TunnelConfig]] = field(default_factory=list)
    forward_tunnels: list[ForwardServer] = field(init=False, repr=False, hash=False, compare=False,
                                                 default_factory=list)
    ssh_client: SSHClient = field(init=False, repr=False, hash=False, compare=False,
                                  default_factory=SSHClient)
    sftp_client: paramiko.SFTPClient = field(init=False, repr=False, hash=False, compare=False, default=None)
    session: paramiko.Channel = field(init=False, repr=False, hash=False, compare=False, default=None)
    ssh_shell: paramiko.Channel | ProxyCommand = field(init=False, repr=False, hash=False, compare=False, default=None)
    transport: paramiko.Transport = field(init=False, repr=False, hash=False, compare=False, default=None)
    screen: pyte.HistoryScreen = field(init=False, repr=False, hash=False, compare=False, default=None)
    stream: pyte.Stream = field(init=False, repr=False, hash=False, compare=False, default=None)
    receive_thread: threading.Thread = field(init=False, repr=False, hash=False, compare=False, default=None)
    shell_active_event: threading.Event = field(init=False, repr=False, hash=False, compare=False, default_factory=threading.Event)
    receive_callback: Callable[[Optional[bytes]], None] = None

    def full_name(self) -> str:
        name = self.name or self.host
        if self.username:
            name += f' ({self.username})'
        return name

    def connect_with_proxy_command(self) -> ProxyCommand:
        return ProxyCommand(self.proxy_command)

    def connect(self, passphrase: str = None, password: str = None, sock: socket.socket = None,
                jump_hosts_passwords: dict[str, ProxyJumpPasswords] = None,
                interactive_login_handler: Callable[[str, str, list[str]], list[str]] = None,
                ask_password_callback: Callable[[str], str] = None) -> None:
        """
        Raises:
        BadHostKeyException – if the server’s host key could not be verified

        Raises:
        AuthenticationException – if authentication failed

        Raises:
        SSHException – if there was any other error connecting or establishing an SSH session

        Raises:
        socket.error – if a socket error occurred while connecting
        """
        if self.proxy_command:
            self.ssh_shell = self.connect_with_proxy_command()
            self.transport = paramiko.Transport(self.ssh_shell)
            return
        self.set_known_hosts_policy()
        if self.host_keys_file:
            self.ssh_client.load_host_keys(self.host_keys_file)
        else:
            self.ssh_client.load_system_host_keys()

        if self.proxy_host:
            match self.proxy_version:
                case "socks5":
                    proxy_type = ProxyType.SOCKS5
                case "socks4":
                    proxy_type = ProxyType.SOCKS4
                case "http":
                    proxy_type = ProxyType.HTTP
                case _:
                    raise UnknownSocksVersion(
                        f"Socks{self.proxy_version} is not recognised. Only socks4, socks5 and http are accepted")
            proxy = Proxy.create(proxy_type, self.proxy_host, self.proxy_port, self.proxy_username, self.proxy_password,
                                 self.socks_rdns)
            sock = proxy.connect(self.host, self.port, timeout=self.timeout)
        elif self.jump_hosts:
            jump_hosts = self.jump_hosts.copy()
            jump = jump_hosts.pop(-1)
            jump_client = replace(self, jump_hosts=jump_hosts, socks_tunnels=[], tunnels=[], **jump)
            passwords = (jump_hosts_passwords or {}).pop(jump['host'], {})
            password = passwords.get('password')
            passphrase = passwords.get('passphrase')
            jump_client.connect(password=password, passphrase=passphrase, sock=sock, jump_hosts_passwords=passwords)
            self.sub_clients.append(jump_client)
            jump_transport = jump_client.transport
            sock = jump_transport.open_channel(
                kind='direct-tcpip',
                dest_addr=(self.host, self.port),
                src_addr=jump_transport.getpeername(),
            )
        try:
            self.ssh_client.connect(self.host, port=self.port, username=self.username, password=password,
                                    key_filename=self.key_filename, timeout=self.timeout, sock=sock,
                                    allow_agent=self.allow_agent, look_for_keys=self.look_for_keys, compress=self.compress,
                                    gss_auth=self.gss_auth, gss_kex=self.gss_kex, gss_deleg_creds=self.gss_deleg_creds,
                                    gss_host=self.gss_host, banner_timeout=self.banner_timeout,
                                    auth_timeout=self.auth_timeout, gss_trust_dns=self.gss_trust_dns, passphrase=passphrase,
                                    disabled_algorithms=self.disabled_algorithms)
        except paramiko.SSHException as e:   # Suggest PR for paramiko to raise AuthenticationException instead
            self.transport = self.ssh_client.get_transport()         # As paramiko raises SSHException in case authentication fails, need to check if it's because Authentication failed or something else
            if not self.transport or not self.transport.is_active():
                raise           # Connection error not related to authentication
            try:
                if interactive_login_handler:
                    self.transport.auth_interactive(self.username, interactive_login_handler)
                else:
                    self.transport.auth_interactive_dumb(self.username)
            except paramiko.BadAuthenticationType as e:
                if "password" in str(e) and not password and ask_password_callback:
                    password = ask_password_callback(self.username)
                    self.transport.auth_password(self.username, password)
                else:
                    raise paramiko.AuthenticationException(
                        "Unable to authenticate to this server with provided authentication methods and interactive login not enabled on server side. ")
        else:
            self.transport = self.ssh_client.get_transport()
        if self.keepalive_interval:
            self.transport.set_keepalive(self.keepalive_interval)
        self.session = self.transport.open_session()
        for t in self.socks_tunnels:
            self.ssh_client.open_socks_proxy(t[0], t[1])
        for t in self.tunnels:
            self.setup_tunnel(t)

    def scroll_up(self):
        self.screen.prev_page()
        self.receive_callback(None)

    def scroll_down(self):
        self.screen.next_page()
        self.receive_callback(None)

    def resize_terminal(self, width: int = None, height: int = None, logger=None):
        width = width or self.screen.columns
        height = height or self.screen.lines
        if self.ssh_shell:
            logger.info('Resizing screen')
            self.screen.resize(height, width)
            logger.info('Resizing pty')
            self.ssh_shell.resize_pty(width, height)
            if self.receive_callback:
                self.receive_callback(None)

    def setup_tunnel(self, tunnel: TunnelConfig):
        forward_server = forward_tunnel(tunnel['src'][1], tunnel['dst'][0], tunnel['dst'][1], self.transport,
                                        tunnel['src'][0])
        self.forward_tunnels.append(forward_server)

    def wait_started(self):
        for server in self.forward_tunnels:
            server.wait_started(10)

    def set_known_hosts_policy(self):
        match self.known_hosts_policy:
            case 'reject':
                policy = paramiko.RejectPolicy
            case 'auto':
                policy = paramiko.AutoAddPolicy
            case 'warn':
                policy = paramiko.WarningPolicy
            case _:
                raise UnknownKnownHostsPolicy(f'{self.known_hosts_policy} not a recognised known_hosts policy')
        self.ssh_client.set_missing_host_key_policy(policy)

    def invoke_shell(self, width: int = 80, height: int = 24, width_pixels: int = 0, height_pixels: int = 0,
                     history: int = 100, recv_callback: Callable[[], None] = None):
        """
        Raises:	SSHException – if the request was rejected or the channel was closed
        """
        if not self.transport:
            raise NotConnectedException
        if not self.proxy_command:
            self.ssh_shell = self.transport.open_session()
            if self.environment:
                self.ssh_shell.update_environment(self.environment)
            if self.x11:
                x11_thread = register_x11(self.ssh_shell, screen_number=self.x11_screen_number,
                                          auth_protocol=self.x11_auth_protocol,
                                          x11_try_start_server=self.x11_try_start_server)
                self.threads.append(x11_thread)
            self.ssh_shell.get_pty(self.term, width, height, width_pixels, height_pixels)
            self.ssh_shell.invoke_shell()
        self.screen = pyte.HistoryScreen(width, height, history=history)
        self.stream = pyte.Stream(self.screen)
        self.shell_active_event.set()
        self.receive_callback = recv_callback
        self.receive_thread = threading.Thread(target=self.receive_always,
                                               daemon=True)
        self.receive_thread.start()

    def reconnect_existing(self, sock):
        self.ssh_client.connect(self.host, sock=sock)

    def duplicate(self) -> 'Client':
        """
        Raises:
        BadHostKeyException – if the server’s host key could not be verified

        Raises:
        AuthenticationException – if authentication failed

        Raises:
        SSHException – if there was any other error connecting or establishing an SSH session

        Raises:
        socket.error – if a socket error occurred while connecting
        """

        if not self.transport:
            raise NotConnectedException
        sock = self.transport.sock
        client = replace(self)
        client.reconnect_existing(sock)
        return client

    @property
    def shell_active(self) -> bool:
        return self.shell_active_event.is_set()

    def send(self, text: str):
        if not self.ssh_shell:
            raise NoShellException
        try:
            self.ssh_shell.sendall(text.encode('utf-8'))
        except OSError:
            self.shell_active_event.clear()

    def receive(self):
        data = self.ssh_shell.recv(9999)
        logging.debug('Received data %s bytes', len(data))
        logging.debug('Received data %s', data)
        if data:
            self.stream.feed(data.decode('utf-8', errors='ignore'))
        else:
            logger.debug('Clearing shell event')
            self.shell_active_event.clear()
        if self.receive_callback:
            self.receive_callback(data)

    def receive_always(self):
        if not self.ssh_shell:
            raise NoShellException
        while self.shell_active_event.is_set():
            self.receive()

    def display_screen(self) -> list[str]:
        if self.screen:
            return self.screen.display
        return []

    def cursors(self) -> tuple[int, int]:
        return self.screen.cursor.y, self.screen.cursor.x,

    def display_screen_line_changes(self) -> dict[int, dict[int, pyte.screens.Char]]:
        changes = {line: self.screen.buffer[line] for line in self.screen.dirty}
        self.screen.dirty.clear()
        return changes

    def display_screen_as_text(self) -> str:
        display = self.display_screen()
        return '\n'.join(display)

    def parallel_sftp(self) -> 'Client':
        if self.proxy_command:
            raise NotAvailableInProxyCommandMode('SFTP')
        client = self.duplicate()
        client.ssh_client.open_sftp()
        return client

    def exec_command(self, command) -> None:
        self.ssh_shell.exec_command(command)

    def command_result(self, command: str, bufsize: int = -1, timeout: int = 3, repeat: int = 1,
                       delay: int = 5) -> Generator[str, None, None]:
        """
        This is specifically for running a single command and returning the result. There should always be a timeout
        """
        if self.proxy_command:
            raise NotAvailableInProxyCommandMode('Running a command')
        for i in range(0, repeat):
            stdin, stdout, stderr = self.ssh_client.exec_command(command, bufsize=bufsize, timeout=timeout,
                                                                 environment=self.environment)
            text = stdin.read() + stderr.read()  # fix
            yield text.decode()
            time.sleep(delay)

    def sftp(self, passphrase: str = None, password: str = None) -> None:
        if self.proxy_command:
            raise NotAvailableInProxyCommandMode('SFTP')
        self.connect(passphrase=passphrase, password=password)
        self.ssh_client.open_sftp()

    def close(self):
        self.shell_active_event.clear()
        for server in self.forward_tunnels:
            server.shutdown()
        self.ssh_client.close()
        if self.transport:
            self.transport.close()
        for client in self.sub_clients:
            client.close()

    def wait_closed(self):
        logger.debug('joining receive thread')
        self.receive_thread.join()
        logger.debug('joining x11 thread')
        for thread in self.threads:
            thread.join()
        logger.debug('x11 thread joined')

    def save(self):
        pass


def send_one_command(): ...

