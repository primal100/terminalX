from typing import Dict, Iterable, Literal, Tuple, Union
from pathlib import Path

File = Union[str, Path]
DisabledAlgorithms = Dict[str, Iterable[str]]
StringDict = Dict[str, str]
KnownHostsPolicy = Literal["reject", "auto", "warning"]
ProxyVersion = Literal["socks5", "socks4", "http"]
TunnelConfig = Dict[str, Tuple[str, int]]

