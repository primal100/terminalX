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
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA.

# Additional utilites added to support SOCKS PROXY
# From https://github.com/paramiko/paramiko/pull/1873/files#diff-12d25726b6e93483154a1601bc1da4a363c48e9c7f4792238d3effde4bd01e93


import socket


def families_and_addresses(hostname, port):
    """
    Yield pairs of address families and addresses to try for connecting.
    :param str hostname: the server to connect to
    :param int port: the server port to connect to
    :returns: Yields an iterable of ``(family, address)`` tuples
    """
    guess = True
    addrinfos = socket.getaddrinfo(
        hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM
    )
    for (family, socktype, proto, canonname, sockaddr) in addrinfos:
        if socktype == socket.SOCK_STREAM:
            yield family, sockaddr
            guess = False

    # some OS like AIX don't indicate SOCK_STREAM support, so just
    # guess. :(  We only do this if we did not get a single result marked
    # as socktype == SOCK_STREAM.
    if guess:
        for family, _, _, _, sockaddr in addrinfos:
            yield family, sockaddr


def ip_addr_to_str(addr):
    """
    Return a protocol version aware formatted string for an IP address tuple.
    """
    if ":" in addr[0]:
        return "[{}]:{}".format(addr[0], addr[1])
    return "{}:{}".format(addr[0], addr[1])
