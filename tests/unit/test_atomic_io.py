from __future__ import annotations

import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from rally.services.atomic_io import write_atomic, write_atomic_bytes


class AtomicIoTests(unittest.TestCase):
    def test_write_atomic_round_trips_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "state.yaml"
            write_atomic(target, "hello: world\n")
            self.assertEqual(target.read_text(encoding="utf-8"), "hello: world\n")

    def test_write_atomic_creates_parent_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "nested" / "deep" / "state.yaml"
            write_atomic(target, "x: 1\n")
            self.assertTrue(target.is_file())

    def test_write_atomic_leaves_no_tmp_files_on_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "state.yaml"
            write_atomic(target, "a: 1\n")
            siblings = sorted(p.name for p in Path(temp_dir).iterdir())
            self.assertEqual(siblings, ["state.yaml"])

    def test_write_atomic_cleans_tmp_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "state.yaml"
            original = b"original\n"
            target.write_bytes(original)

            def boom(_self: object, *_args: object, **_kwargs: object) -> int:
                raise OSError("simulated write failure")

            with mock.patch(
                "tempfile._TemporaryFileWrapper.write",
                new=boom,
                create=True,
            ):
                with self.assertRaises(OSError):
                    write_atomic(target, "new content\n")

            # Original file untouched.
            self.assertEqual(target.read_bytes(), original)
            # No orphan tmp files remain.
            siblings = sorted(p.name for p in Path(temp_dir).iterdir())
            self.assertEqual(siblings, ["state.yaml"])

    def test_write_atomic_replaces_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "state.yaml"
            target.write_text("old\n", encoding="utf-8")
            write_atomic(target, "new\n")
            self.assertEqual(target.read_text(encoding="utf-8"), "new\n")

    def test_write_atomic_bytes_writes_binary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "data.bin"
            payload = bytes(range(256))
            write_atomic_bytes(target, payload)
            self.assertEqual(target.read_bytes(), payload)

    def test_concurrent_writers_never_produce_torn_content(self) -> None:
        # Two threads race to rewrite the same file. Because each write is
        # atomic (tempfile + rename), the final content must equal exactly one
        # of the two payloads — never an interleaving.
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "state.yaml"
            payload_a = "a" * 4096 + "\n"
            payload_b = "b" * 4096 + "\n"
            start = threading.Event()

            def writer(text: str) -> None:
                start.wait()
                for _ in range(50):
                    write_atomic(target, text)

            threads = [
                threading.Thread(target=writer, args=(payload_a,)),
                threading.Thread(target=writer, args=(payload_b,)),
            ]
            for thread in threads:
                thread.start()
            start.set()
            for thread in threads:
                thread.join()

            content = target.read_text(encoding="utf-8")
            self.assertIn(content, {payload_a, payload_b})
            # No stray tmp files.
            siblings = sorted(p.name for p in Path(temp_dir).iterdir())
            self.assertEqual(siblings, ["state.yaml"])

    def test_write_atomic_survives_missing_target_dir_race(self) -> None:
        # Even if the parent directory doesn't exist yet, the helper creates
        # it. This protects against fresh run dirs with no state.yaml yet.
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "runs" / "active" / "DMO-1" / "state.yaml"
            write_atomic(target, "status: pending\n")
            self.assertTrue(target.is_file())

    def test_fsync_dir_failure_does_not_fail_write(self) -> None:
        # Some filesystems refuse directory fsync. The write must still succeed.
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "state.yaml"
            with mock.patch("rally.services.atomic_io.os.fsync") as fake:
                # First call is file fsync (must succeed). Second is dir fsync
                # (we simulate a filesystem that refuses).
                call_count = {"n": 0}

                def side_effect(fd: int) -> None:
                    call_count["n"] += 1
                    if call_count["n"] >= 2:
                        raise OSError("ENOTSUP")

                fake.side_effect = side_effect
                write_atomic(target, "ok\n")
            self.assertEqual(target.read_text(encoding="utf-8"), "ok\n")


if __name__ == "__main__":
    unittest.main()
