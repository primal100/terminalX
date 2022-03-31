from typing import Iterable, Literal, Optional, TypedDict
from pathlib import Path

File = str | Path
DisabledAlgorithms = dict[str, Iterable[str]]
StringDict = dict[str, str]
KnownHostsPolicy = Literal["reject", "auto", "warning"]
ProxyVersion = Literal["socks5", "socks4", "http"]


class TunnelConfig(TypedDict):
    src: tuple[Optional[str], int]
    dst: tuple[str, int]


# Some paramaters listed as NotRequired with plan to use new feature coming in 3.11 when available


class ProxyJump(TypedDict, total=False):
    host: str
    port: Optional[int]                     # NotRequired
    username: Optional[str]                 # NotRequired
    key_filename: Optional[File]            # NotRequired


class ProxyJumpPasswords(TypedDict, total=False):
    password: Optional[str]                 # NotRequired
    passphrase: Optional[str]               # NotRequired
