"""Bounded local command execution. Process groups are cleanup, not a sandbox."""
from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import threading
import time


def _stop(process: subprocess.Popen) -> str | None:
    if os.name == "posix":
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                return
            except PermissionError:
                if process.poll() is None:
                    process.kill()
                return 'process_group_cleanup_denied'
            if sig == signal.SIGTERM:
                time.sleep(0.05)
    else:
        # Windows support is best effort; the POSIX cleanup contract is tested.
        try:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        except (OSError, subprocess.SubprocessError):
            if process.poll() is None:
                process.kill()


def execute(command: list[str], *, cwd: Path, log: Path, timeout: float,
            max_output_bytes: int = 4 * 1024 * 1024, env: dict | None = None) -> dict:
    """Drain a pipe with a fixed memory/log budget; kill remaining group members."""
    started = time.monotonic()
    log.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    error, code = None, None
    size = [0, 0]
    overflow, reader_failed = threading.Event(), threading.Event()
    process = None
    with log.open("wb") as stream:
        log.chmod(0o600)
        try:
            process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       start_new_session=os.name == "posix")
        except OSError as exc:
            error = "cannot_execute"
            stream.write(f"HARNESS: cannot execute ({type(exc).__name__}).\n".encode())
        if process is not None:
            def drain():
                try:
                    while block := os.read(process.stdout.fileno(), 65536):
                        size[0] += len(block)
                        keep = min(len(block), max(0, max_output_bytes - size[1]))
                        if keep:
                            stream.write(block[:keep])
                            size[1] += keep
                        if size[0] > max_output_bytes:
                            overflow.set()
                except (OSError, ValueError):
                    reader_failed.set()
            reader = threading.Thread(target=drain, daemon=True)
            reader.start()
            try:
                while process.poll() is None or reader.is_alive():
                    if overflow.is_set():
                        error = "output_limit"
                        break
                    if reader_failed.is_set():
                        error = "output_read_error"
                        break
                    if time.monotonic() - started >= timeout:
                        error = "timeout"
                        break
                    time.sleep(0.01)
            finally:
                cleanup_error = _stop(process)
                if cleanup_error:
                    error = cleanup_error
                code = process.wait(timeout=5)
                reader.join(timeout=2)
                if reader.is_alive():
                    error = error or "output_stream_open"
                else:
                    process.stdout.close()
            if overflow.is_set() and error != 'process_group_cleanup_denied':
                error = "output_limit"
            if error:
                stream.write(f"\nHARNESS: {error}; result is not a pass.\n".encode())
    return {"exit_code": code, "error": error, "output_bytes": size[0],
            "retained_bytes": size[1], "duration_seconds": round(time.monotonic() - started, 3)}
