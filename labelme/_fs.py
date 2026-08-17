from __future__ import annotations

import os
import stat
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from loguru import logger


def _read_default_new_file_mode() -> int:
    """The mode a plain `open(path, "x")` would give a brand-new file.

    `tempfile.mkstemp` ignores the umask on purpose and always creates at
    0o600; there is no way to inspect the umask without a paired set/restore,
    so a new file still lands at the mode callers would expect instead of
    that stricter default. Not thread-safe: another thread creating a file
    in the gap between the two `os.umask` calls sees the probe value.
    """
    current_umask = os.umask(0o022)
    os.umask(current_umask)
    return 0o666 & ~current_umask


def atomic_write(
    path: Path,
    write: Callable[[TextIO], None],
    *,
    preserve_mode: bool = False,
) -> None:
    """Replace `path` atomically: write via a temp file, then `os.replace`.

    `path` is left untouched if `write`, close, or the replace fails, and the
    temp file is removed. No `fsync` is forced, so this bounds a serialization
    or filesystem failure to "never truncate the last good file", not to full
    crash durability. `os.replace` swaps the directory entry itself, so a
    symlinked or hardlinked `path` loses that link identity on replacement.

    `preserve_mode` carries `path`'s existing POSIX mode bits onto the
    replacement (or, for a brand-new `path`, the mode a plain `open()` would
    have used); it has no effect on Windows, which has no such bits, and a
    filesystem that rejects `chmod` (FAT/exFAT/some network mounts) degrades
    to the temp file's private default rather than losing the write.
    """
    should_preserve_mode = preserve_mode and os.name != "nt"
    existing_mode: int | None = None
    if should_preserve_mode:
        try:
            existing_mode = stat.S_IMODE(path.stat().st_mode)
        except FileNotFoundError:
            pass
    # A short, target-name-independent prefix keeps the temp path well under
    # POSIX filename limits even when `path` itself is close to that limit.
    fd, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            write(f)
            if should_preserve_mode:
                # chmod the still-open fd (not the path) so a symlink swapped
                # in after close can't redirect it, and only after the write
                # completes: mkstemp's own 0o600 keeps the temp file
                # maximally private for the whole write, widening only once
                # there is a complete file behind it.
                mode = (
                    existing_mode
                    if existing_mode is not None
                    else _read_default_new_file_mode()
                )
                try:
                    os.fchmod(f.fileno(), mode)
                except OSError:
                    # Preserving mode bits is cosmetic; losing a completed
                    # write over it is not. Keep mkstemp's private default.
                    logger.warning("failed to chmod {!r}, keeping 0o600", path)
        os.replace(temporary_name, path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise
