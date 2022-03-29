import paramiko
import os


class ProxyCommand(paramiko.ProxyCommand):

    def recv(self, size: int):
        """
        Windows Receive Issue: https://github.com/paramiko/paramiko/issues/512
        Workaround taken from https://github.com/JulianEberius/paramiko/blob/bb1f795db46891961b6a816df3c59e132de7f211/paramiko/proxy.py
        Read from the standard output of the forked program.
        On Windows select() only works on sockets, so the loop will fail on this
        platform. Therefore, use a simple blocking call in this case.
        :param int size: how many chars should be read
        :return: the string of bytes read, which may be shorter than requested
        """
        if os.name == 'nt':
            try:
                return os.read(self.process.stdout.fileno(), size)
            except IOError as e:
                raise paramiko.ProxyCommandFailure(" ".join(self.cmd), e.strerror)
        else:
            return super().recv(size)

    def sendall(self, content: bytes) -> int:
        """
        Add sendall command to provide compatibility with paramiko Channels
        """
        return self.send(content)
