# Extended paramiko SSH Client to support SOCKS Proxy
# From https://github.com/paramiko/paramiko/pull/1873/files#diff-beeef3198e4e0c451d6f4b07f625af72ba815566e85397a123200ef8e4eca45d

from paramiko import SSHClient as ParamikoSSHClient
from .socks_proxy import SOCKSProxy


class SSHClient(ParamikoSSHClient):
    def __init__(self):
        super().__init__()
        self._socks_proxies = []

    def close(self):
        for proxy in self._socks_proxies:
            proxy.close()
        super().close()

    def open_socks_proxy(self, bind_address="localhost", port=1080):
        """
        Start a SOCKS5 proxy and make it available on a local socket.
        :param str bind_address: the interface to bind to
        :param int port: the port to bind to
        :return: a new `.SOCKSProxy` object
        """
        socks_proxy = SOCKSProxy(self._transport, bind_address, port)
        self._socks_proxies.append(socks_proxy)
        return socks_proxy

    def get_socks_proxies(self):
        """
        Return the list of all running SOCKS proxies instances.
        :return: list of running `.SOCKSProxy` objects for this SSH client
        """
        return self._socks_proxies
