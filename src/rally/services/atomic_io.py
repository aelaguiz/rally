"""Crash-safe file writes.

Rally's runs live entirely on disk, so state files must survive process death
and host reboots. A naive ``path.write_text`` can leave a half-written file if
the writer dies mid-call or if the power cuts between the ``write`` and the
next write. These helpers give us the POSIX-native transactional primitives:

  1. Write the new content to a sibling temp file.
  2. ``fsync`` the file so the bytes are durable on the storage device.
  3. ``os.replace`` the temp file over the target (atomic on POSIX).
  4. ``fsync`` the parent directory so the rename itself is durable.

On success the target either has the old content (writer died) or the full new
content — never a partial file.

Unix-only: Rally is Python 3.14+ and documented as POSIX. Windows fsync of a
directory handle is a no-op/error, so we gate the dir-fsync on non-Windows.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

__all__ = ["write_atomic", "write_atomic_bytes"]


def write_atomic(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Atomically replace ``path`` with ``text``."""
    write_atomic_bytes(path, text.encode(encoding))


def write_atomic_bytes(path: Path, data: bytes) -> None:
    """Atomically replace ``path`` with raw ``data`` bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Temp file is created in the same directory so os.replace is a same-fs
    # rename (atomic). delete=False because we rename it into place ourselves.
    tmp = tempfile.NamedTemporaryFile(
        mode="wb",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    tmp_path = Path(tmp.name)
    try:
        try:
            tmp.write(data)
            tmp.flush()
            os.fsync(tmp.fileno())
        finally:
            tmp.close()
        os.replace(tmp_path, path)
    except BaseException:
        # Clean up the orphan tmp file on any failure (including KeyboardInterrupt).
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise
    _fsync_dir(path.parent)


def _fsync_dir(directory: Path) -> None:
    if os.name != "posix":
        return
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    except OSError:
        # Some filesystems (NFS, certain FUSE mounts) refuse dir fsync. The
        # rename itself is still durable on any sane filesystem; we'd rather
        # soldier on than fail the write.
        pass
    finally:
        os.close(fd)
