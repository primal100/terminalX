from typing import Dict, Iterable, Literal, Tuple, Union
from pathlib import Path

File = Union[str, Path]
DisabledAlgorithms = Dict[str, Iterable[str]]
StringDict = Dict[str, str]
KnownHostsPolicy = Literal["reject", "auto", "warning"]
TunnelConfig = Dict[str, Tuple[str, int]]
