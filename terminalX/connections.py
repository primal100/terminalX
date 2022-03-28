import paramiko
import pyte
from dataclasses import dataclass, field, replace
import threading
import time

from .forwarder import forward_tunnel, ForwardServer
from .types import DisabledAlgorithms, StringDict, File, KnownHostsPolicy, TunnelConfig
from typing import Dict, Generator, List, Tuple


class NotConnectedException(BaseException):
    message = "SSH Client is not yet connected. Call the .connect() method first"


class NoShellException(BaseException):
    message = "SSH Client shell does not exist. Call the .invoke_shell() method first"


@dataclass
class Client:
    host: str
    port: int = 22
    username: str = None
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
    known_hosts_policy: KnownHostsPolicy = "auto"
    jump_host: str = None
    jump_port: int = 22
    jump_username: str = None
    socks_host: str = None
    socks_port: int = None
    socks_username: str = None
    tunnels: List[TunnelConfig] = field(default_factory=list)
    forward_tunnels: List[ForwardServer] = field(init=False, repr=False, hash=False, compare=False,
                                                 default_factory=list)
    ssh_client: paramiko.SSHClient = field(init=False, repr=False, hash=False, compare=False,
                                           default_factory=paramiko.SSHClient)
    sftp_client: paramiko.SFTPClient = field(init=False, repr=False, hash=False, compare=False, default=None)
    ssh_shell: paramiko.Channel = field(init=False, repr=False, hash=False, compare=False, default=None)
    transport: paramiko.Transport = field(init=False, repr=False, hash=False, compare=False, default=None)
    screen: pyte.Screen = field(init=False, repr=False, hash=False, compare=False, default=None)
    stream: pyte.Stream = field(init=False, repr=False, hash=False, compare=False, default=None)
    receive_thread: threading.Thread = field(init=False, repr=False, hash=False, compare=False, default=None)
    shell_active: threading.Event = field(init=False, repr=False, hash=False, compare=False, default_factory=threading.Event)

    def connect(self, passphrase: str = None, password: str = None) -> None:
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
        self.set_known_hosts_policy()
        if self.host_keys_file:
            self.ssh_client.load_host_keys(self.host_keys_file)
        else:
            self.ssh_client.load_system_host_keys()
        self.ssh_client.connect(self.host, port=self.port, username=self.username, password=password,
                                key_filename=self.key_filename, timeout=self.timeout,
                                allow_agent=self.allow_agent, look_for_keys=self.look_for_keys, compress=self.compress,
                                gss_auth=self.gss_auth, gss_kex=self.gss_kex, gss_deleg_creds=self.gss_deleg_creds,
                                gss_host=self.gss_host, banner_timeout=self.banner_timeout,
                                auth_timeout=self.auth_timeout, gss_trust_dns=self.gss_trust_dns, passphrase=passphrase,
                                disabled_algorithms=self.disabled_algorithms)
        self.transport = self.ssh_client.get_transport()
        if self.keepalive_interval:
            self.transport.set_keepalive(self.keepalive_interval)
        for t in self.tunnels:
            self.setup_tunnel(t)

    def setup_tunnel(self, tunnel: TunnelConfig):
        forward_server = forward_tunnel(tunnel['src'][1], tunnel['dst'][0], tunnel['dst'][1], self.transport,
                                        tunnel['src'][0])
        self.forward_tunnels.append(forward_server)

    def wait_started(self):
        for server in self.forward_tunnels:
            server.wait_started(10)

    def set_known_hosts_policy(self):
        policies = {
            'reject': paramiko.RejectPolicy,
            'auto': paramiko.AutoAddPolicy,
            'warn': paramiko.WarningPolicy
        }
        policy = policies[self.known_hosts_policy]
        self.ssh_client.set_missing_host_key_policy(policy)

    def invoke_shell(self, width: int = 80, height: int = 24, width_pixels: int = 0, height_pixels: int = 0,
                     history: int = 100):
        """
        Raises:	SSHException – if the request was rejected or the channel was closed
        """
        if not self.transport:
            raise NotConnectedException
        self.ssh_shell = self.ssh_client.invoke_shell(term=self.term, width=width, height=height,
                                                      width_pixels=width_pixels, height_pixels=height_pixels,
                                                      environment=self.environment)
        if self.x11:
            self.ssh_shell.request_x11(screen_number=self.x11_screen_number, auth_protocol=self.x11_auth_protocol)
        self.screen = pyte.HistoryScreen(80, 24, history=history)
        self.stream = pyte.Stream(self.screen)
        self.shell_active.set()
        self.receive_thread = threading.Thread(target=self.receive_always)
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

    def send(self, text: str):
        if not self.ssh_shell:
            raise NoShellException
        self.ssh_shell.sendall(text.encode('utf-8'))

    def receive(self):
        data = self.ssh_shell.recv(9999)
        if data:
            self.stream.feed(data.decode())

    def receive_always(self, interval: int = 0.25):
        if not self.ssh_shell:
            raise NoShellException
        while self.shell_active.is_set():
            self.receive()

    def display_screen(self) -> List[str]:
        if self.screen:
            return self.screen.display
        return []

    def cursors(self) -> Tuple[int, int]:
        return self.screen.cursor.x, self.screen.cursor.y

    def display_screen_as_text(self) -> str:
        display = self.display_screen()
        return '\n'.join(display)

    def parallel_sftp(self) -> 'Client':
        client = self.duplicate()
        client.ssh_client.open_sftp()
        return client

    def command_result(self, command: str, bufsize: int = -1, timeout: int = 3, repeat: int = 1,
                       delay: int = 5) -> Generator[str, None, None]:
        """
        This is specifically for running a single command and returning the result. There should always be a timeout
        """
        for i in range(0, repeat):
            stdin, stdout, stderr = self.ssh_client.exec_command(command, bufsize=bufsize, timeout=timeout,
                                                                 environment=self.environment)
            text = stdin.read() + stderr.read()  # fix
            yield text.decode()
            time.sleep(delay)

    def sftp(self, passphrase: str = None, password: str = None) -> None:
        self.connect(passphrase=passphrase, password=password)
        self.ssh_client.open_sftp()

    def close(self):
        for server in self.forward_tunnels:
            server.shutdown()
        self.ssh_client.close()
        self.shell_active.clear()

    def save(self):
        pass


def send_one_command(): ...

