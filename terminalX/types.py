from typing import Dict, Iterable, Union
from pathlib import Path

File = Union[str, Path]
DisabledAlgorithms = Dict[str, Iterable[str]]
EnvironmentDict = Dict[str, str]
