import os
import platform


def is_wsl() -> bool:
    return os.name == 'posix' and 'microsoft' in platform.uname().release.lower()


def is_aix() -> bool:
    return sys.platform.startswith("aix")
