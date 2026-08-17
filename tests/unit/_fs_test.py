from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import TextIO

import pytest

from labelme import _fs
from labelme._fs import atomic_write


@pytest.mark.skipif(os.name == "nt", reason="requires POSIX file modes")
def test_atomic_write_keeps_temp_file_private_during_write(tmp_path: Path) -> None:
    """The temp file must stay at mkstemp's private default while content is
    still being written, even when the target's own mode is far wider."""
    target = tmp_path / "target.txt"
    target.write_text("last good", encoding="utf-8")
    target.chmod(0o644)

    observed_modes: list[int] = []

    def _write(f: TextIO) -> None:
        [temp] = [p for p in tmp_path.iterdir() if p != target]
        observed_modes.append(stat.S_IMODE(temp.stat().st_mode))
        f.write("new content")

    atomic_write(target, _write, preserve_mode=True)

    assert observed_modes == [0o600]
    assert stat.S_IMODE(target.stat().st_mode) == 0o644
    assert target.read_text(encoding="utf-8") == "new content"


@pytest.mark.skipif(os.name == "nt", reason="requires POSIX file modes")
def test_atomic_write_survives_chmod_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A filesystem that rejects chmod (FAT/exFAT/some network mounts) must
    not cost the user a completed write over a cosmetic mode mismatch."""
    target = tmp_path / "target.txt"
    target.write_text("last good", encoding="utf-8")
    target.chmod(0o644)

    def _fail_chmod(_fd: int, _mode: int) -> None:
        raise OSError("chmod not supported")

    monkeypatch.setattr(_fs.os, "fchmod", _fail_chmod)

    atomic_write(target, lambda f: f.write("new content"), preserve_mode=True)

    assert target.read_text(encoding="utf-8") == "new content"
    # mkstemp's own default survives, since the chmod that would have
    # widened it to 0o644 failed.
    assert stat.S_IMODE(target.stat().st_mode) == 0o600


def test_atomic_write_removes_temp_file_on_failure(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("last good", encoding="utf-8")

    def _fail(_f: TextIO) -> None:
        raise OSError("boom")

    with pytest.raises(OSError, match="boom"):
        atomic_write(target, _fail)

    assert target.read_text(encoding="utf-8") == "last good"
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.skipif(os.name == "nt", reason="requires POSIX file modes")
def test_atomic_write_uses_default_mode_for_new_file(tmp_path: Path) -> None:
    reference = tmp_path / "reference.txt"
    reference.write_text("", encoding="utf-8")
    target = tmp_path / "new.txt"

    atomic_write(target, lambda f: f.write("content"), preserve_mode=True)

    assert stat.S_IMODE(target.stat().st_mode) == stat.S_IMODE(reference.stat().st_mode)


@pytest.mark.skipif(os.name == "nt", reason="requires POSIX file modes")
def test_atomic_write_ignores_existing_mode_when_not_requested(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("last good", encoding="utf-8")
    target.chmod(0o644)

    atomic_write(target, lambda f: f.write("new content"))

    assert target.read_text(encoding="utf-8") == "new content"
    # mkstemp's own default, since preserve_mode=False never chmods.
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
