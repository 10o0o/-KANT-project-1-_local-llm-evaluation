"""Low-level, verdict-neutral process isolation and output collection."""

from __future__ import annotations

import math
import os
import selectors
import signal
import subprocess
import time
from dataclasses import dataclass
from os import PathLike
from typing import Mapping, Sequence


READ_SIZE = 64 * 1024


class ProcessCleanupError(RuntimeError):
    """Raised when an owned process does not stop after SIGKILL."""


def _validate_duration(name: str, value: float) -> None:
    try:
        finite = math.isfinite(value)
    except TypeError as exc:
        raise TypeError(f"{name} must be a finite number") from exc
    if not finite or value < 0:
        raise ValueError(f"{name} must be finite and non-negative")


@dataclass(frozen=True)
class CollectedProcessOutput:
    stdout: bytes
    stderr: bytes
    returncode: int | None
    elapsed_seconds: float
    timed_out: bool
    output_limit_exceeded: bool
    pipes_drained: bool


def spawn_isolated(
    args: Sequence[str | PathLike[str]],
    *,
    cwd: str | PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    stdin=subprocess.DEVNULL,
) -> subprocess.Popen[bytes]:
    """Start an owned process group with separate, unbuffered binary pipes."""

    return subprocess.Popen(
        args,
        cwd=cwd,
        env=env,
        stdin=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
        close_fds=True,
        restore_signals=True,
        start_new_session=True,
    )


def _group_exists(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # This should not occur for an owned child, but it still proves that the
        # group exists and must not be treated as successful cleanup.
        return True
    return True


def terminate_process_group(
    process: subprocess.Popen[bytes],
    *,
    grace_seconds: float = 0.25,
    kill_wait_seconds: float = 1.0,
) -> None:
    """Terminate the process group created by :func:`spawn_isolated`.

    The group signal is sent even when the leader has exited because descendants
    can keep inherited stdout/stderr descriptors open after that point.
    """

    _validate_duration("grace_seconds", grace_seconds)
    _validate_duration("kill_wait_seconds", kill_wait_seconds)

    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        if process.poll() is None:
            try:
                process.wait(timeout=kill_wait_seconds)
            except subprocess.TimeoutExpired as exc:
                raise ProcessCleanupError(
                    f"process {process.pid} remained alive after its group disappeared"
                ) from exc
        return

    if process.poll() is None:
        try:
            process.wait(timeout=grace_seconds)
        except subprocess.TimeoutExpired:
            pass

    if _group_exists(process.pid):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    if process.poll() is None:
        try:
            process.wait(timeout=kill_wait_seconds)
        except subprocess.TimeoutExpired as exc:
            raise ProcessCleanupError(
                f"process group {process.pid} did not stop after SIGKILL"
            ) from exc


def collect_bounded_output(
    process: subprocess.Popen[bytes],
    *,
    timeout_seconds: float,
    output_limit_bytes: int,
    cleanup_grace_seconds: float = 0.25,
    cleanup_wait_seconds: float = 1.0,
    drain_timeout_seconds: float = 1.0,
) -> CollectedProcessOutput:
    """Collect stdout/stderr concurrently with one aggregate byte limit.

    Reaching the deadline or observing one byte beyond the aggregate limit
    starts process-group cleanup. Both pipes are then drained concurrently until
    EOF, with a separate bounded drain window. The result contains mechanism
    facts only; callers decide how those facts map to judge verdicts.
    """

    _validate_duration("timeout_seconds", timeout_seconds)
    _validate_duration("cleanup_grace_seconds", cleanup_grace_seconds)
    _validate_duration("cleanup_wait_seconds", cleanup_wait_seconds)
    _validate_duration("drain_timeout_seconds", drain_timeout_seconds)
    if isinstance(output_limit_bytes, bool) or not isinstance(output_limit_bytes, int):
        raise TypeError("output_limit_bytes must be an integer")
    if output_limit_bytes < 0:
        raise ValueError("output_limit_bytes must be non-negative")
    if process.stdout is None or process.stderr is None:
        raise ValueError("process must have separate stdout and stderr pipes")

    start = time.monotonic()
    deadline = start + timeout_seconds
    stdout = bytearray()
    stderr = bytearray()
    streams = ((process.stdout, stdout, "stdout"), (process.stderr, stderr, "stderr"))
    timed_out = False
    output_limit_exceeded = False
    cleanup_started = False
    cleanup_deadline: float | None = None
    pipes_drained = True

    def begin_cleanup() -> None:
        nonlocal cleanup_started, cleanup_deadline
        if cleanup_started:
            return
        cleanup_started = True
        terminate_process_group(
            process,
            grace_seconds=cleanup_grace_seconds,
            kill_wait_seconds=cleanup_wait_seconds,
        )
        cleanup_deadline = time.monotonic() + drain_timeout_seconds

    try:
        with selectors.DefaultSelector() as selector:
            for stream, _buffer, name in streams:
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, data=name)

            while selector.get_map():
                now = time.monotonic()
                if not cleanup_started:
                    if process.poll() is not None:
                        # The leader may have left descendants holding the pipes.
                        begin_cleanup()
                    elif now >= deadline:
                        timed_out = True
                        begin_cleanup()

                # Group cleanup may block for its grace/kill waits. Sample the
                # clock again so that selector timeout never reuses stale time.
                now = time.monotonic()
                if cleanup_deadline is not None and now >= cleanup_deadline:
                    pipes_drained = False
                    break

                wait_until = cleanup_deadline if cleanup_deadline is not None else deadline
                events = selector.select(timeout=max(0.0, wait_until - now))
                if not events:
                    continue

                for key, _mask in events:
                    try:
                        chunk = os.read(key.fileobj.fileno(), READ_SIZE)
                    except BlockingIOError:
                        continue
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue

                    if output_limit_exceeded:
                        continue

                    used = len(stdout) + len(stderr)
                    remaining = output_limit_bytes - used
                    target = stdout if key.data == "stdout" else stderr
                    target.extend(chunk[:remaining])
                    if len(chunk) > remaining:
                        output_limit_exceeded = True
                        begin_cleanup()

            if not cleanup_started:
                remaining = max(0.0, deadline - time.monotonic())
                try:
                    process.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    timed_out = True
                begin_cleanup()
    except BaseException:
        if not cleanup_started:
            try:
                begin_cleanup()
            except Exception:
                # Preserve the original collection failure while still making a
                # best-effort group cleanup attempt.
                pass
        raise
    finally:
        for stream, _buffer, _name in streams:
            stream.close()

    return CollectedProcessOutput(
        stdout=bytes(stdout),
        stderr=bytes(stderr),
        returncode=process.returncode,
        elapsed_seconds=time.monotonic() - start,
        timed_out=timed_out,
        output_limit_exceeded=output_limit_exceeded,
        pipes_drained=pipes_drained,
    )
