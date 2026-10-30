"""Bounded UTF-8 file inputs; FIFOs and symlinks cannot turn reads into waits."""
import os
from pathlib import Path
import stat


def read_regular_text(path: Path, limit: int) -> str:
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError("routing inputs must be regular files")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("routing input changed file type")
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise ValueError("routing input exceeds size limit")
    return content.decode("utf-8")
