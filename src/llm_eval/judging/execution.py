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
from pathlib import Path
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
    termination_reason: str | None


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


def _group_has_live_members(pgid: int, proc_root: Path = Path("/proc")) -> bool:
    """Return whether a Linux process group has a non-zombie member."""

    try:
        entries = list(proc_root.iterdir())
    except OSError:
        return _group_exists(pgid)
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            _prefix, suffix = (entry / "stat").read_text().rsplit(") ", 1)
            fields = suffix.split()
            state = fields[0]
            process_group = int(fields[2])
        except (OSError, ValueError, IndexError):
            continue
        if process_group == pgid and state != "Z":
            return True
    return False


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

    group_deadline = time.monotonic() + kill_wait_seconds
    while _group_has_live_members(process.pid):
        remaining = group_deadline - time.monotonic()
        if remaining <= 0:
            raise ProcessCleanupError(
                f"process group {process.pid} retained live descendants after SIGKILL"
            )
        time.sleep(min(0.01, remaining))

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
    started_at: float | None = None,
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

    if started_at is None:
        start = time.monotonic()
    else:
        _validate_duration("started_at", started_at)
        start = started_at
    deadline = start + timeout_seconds
    stdout = bytearray()
    stderr = bytearray()
    streams = ((process.stdout, stdout, "stdout"), (process.stderr, stderr, "stderr"))
    timed_out = False
    output_limit_exceeded = False
    capture_limit_reached = False
    termination_reason: str | None = None
    elapsed_seconds: float | None = None
    cleanup_started = False
    cleanup_deadline: float | None = None
    pipes_drained = True

    def mark_trigger(reason: str, observed_at: float | None = None) -> None:
        nonlocal termination_reason, elapsed_seconds, timed_out, output_limit_exceeded
        if termination_reason is not None:
            return
        termination_reason = reason
        if elapsed_seconds is None:
            elapsed_seconds = (
                time.monotonic() if observed_at is None else observed_at
            ) - start
        timed_out = reason == "timeout"
        output_limit_exceeded = reason == "output_limit"

    def begin_cleanup(
        reason: str | None = None, observed_at: float | None = None
    ) -> None:
        nonlocal cleanup_started, cleanup_deadline
        if reason is not None:
            mark_trigger(reason, observed_at)
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
                        if elapsed_seconds is None:
                            elapsed_seconds = now - start
                        begin_cleanup()
                    elif now >= deadline:
                        begin_cleanup("timeout", now)

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

                # Selector readiness can arrive at the deadline. Refresh the
                # clock before treating ready bytes as the first resource
                # trigger so a stale pre-select timestamp cannot turn TLE into
                # OLE.
                if not cleanup_started:
                    observed_at = time.monotonic()
                    if process.poll() is None and observed_at >= deadline:
                        begin_cleanup("timeout", observed_at)
                    elif process.poll() is not None:
                        if elapsed_seconds is None:
                            elapsed_seconds = observed_at - start
                        begin_cleanup()

                for key, _mask in events:
                    try:
                        chunk = os.read(key.fileobj.fileno(), READ_SIZE)
                    except BlockingIOError:
                        continue
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue

                    if capture_limit_reached:
                        continue

                    used = len(stdout) + len(stderr)
                    remaining = output_limit_bytes - used
                    target = stdout if key.data == "stdout" else stderr
                    target.extend(chunk[:remaining])
                    if len(chunk) > remaining:
                        capture_limit_reached = True
                        if termination_reason is None:
                            begin_cleanup("output_limit")

            if not cleanup_started:
                remaining = max(0.0, deadline - time.monotonic())
                try:
                    process.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    begin_cleanup("timeout")
                else:
                    elapsed_seconds = time.monotonic() - start
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

    if elapsed_seconds is None:
        elapsed_seconds = time.monotonic() - start

    return CollectedProcessOutput(
        stdout=bytes(stdout),
        stderr=bytes(stderr),
        returncode=process.returncode,
        elapsed_seconds=elapsed_seconds,
        timed_out=timed_out,
        output_limit_exceeded=output_limit_exceeded,
        pipes_drained=pipes_drained,
        termination_reason=termination_reason,
    )
