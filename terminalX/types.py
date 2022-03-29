from typing import Iterable, Literal, Optional, Tuple, TypedDict, Union
from pathlib import Path

File = Union[str, Path]
DisabledAlgorithms = dict[str, Iterable[str]]
StringDict = dict[str, str]
KnownHostsPolicy = Literal["reject", "auto", "warning"]
ProxyVersion = Literal["socks5", "socks4", "http"]


class TunnelConfig(TypedDict):
    src: Tuple[Optional[str], int]
    dst: Tuple[str, int]


class ProxyJump(TypedDict):
    host: str
    port: Optional[int]
    username: Optional[str]
    key_filename: Union[str, Path, None]


class ProxyJumpPasswords(TypedDict):
    password: Optional[str]
    passphrase: Optional[str]
