"""Central command execution.

Every external command (ping, nmap, nmcli, ...) goes through here rather than
scattering ``subprocess`` calls across the UI. Two modes:

* :meth:`CommandRunner.run` -- synchronous, with a timeout, for quick commands.
* :meth:`CommandRunner.run_async` -- runs in a worker thread and streams output
  line by line, so the UI loop keeps drawing. The returned
  :class:`AsyncCommand` can be cancelled and drained for new lines.

Commands are passed as argument lists and run without a shell, so
there is no shell-injection surface. Missing executables (e.g. nmap not
installed) come back as a result with ``error`` set rather than raising, so a
page can show "NOT INSTALLED" instead of crashing.
"""
from __future__ import annotations

import logging
import queue
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

log = logging.getLogger(__name__)

Command = Sequence[str]
LineCallback = Callable[[str], None]
DoneCallback = Callable[["CommandResult"], None]


@dataclass
class CommandResult:
    command: list[str]
    returncode: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0
    timed_out: bool = False
    cancelled: bool = False
    error: Optional[str] = None  # e.g. "not found"

    @property
    def ok(self) -> bool:
        return (
            self.returncode == 0
            and self.error is None
            and not self.timed_out
            and not self.cancelled
        )


class AsyncCommand:
    """A command running in a background thread, streaming its output.

    Poll :meth:`drain_lines` from the UI loop for new output, check
    :attr:`finished`, and read :attr:`result` once done. Call :meth:`cancel` to
    stop it early.
    """

    def __init__(self, command: Command, on_line: Optional[LineCallback] = None,
                 on_done: Optional[DoneCallback] = None) -> None:
        self.command = list(command)
        self._on_line = on_line
        self._on_done = on_done
        self._proc: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._lines: "queue.Queue[str]" = queue.Queue()
        self._result: Optional[CommandResult] = None
        self._done = threading.Event()
        self._cancelled = False
        self._start = 0.0

    def start(self) -> "AsyncCommand":
        self._start = time.monotonic()
        self._thread = threading.Thread(
            target=self._run, name=f"cmd:{self.command[0]}", daemon=True
        )
        self._thread.start()
        return self

    def _elapsed(self) -> float:
        return time.monotonic() - self._start

    def _run(self) -> None:
        try:
            # stderr merged into stdout so streaming can't deadlock on a full
            # stderr pipe, and errors show up inline in the output.
            self._proc = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError:
            self._finish(CommandResult(self.command, error="not found",
                                       duration=self._elapsed()))
            return
        except OSError as exc:
            self._finish(CommandResult(self.command, error=str(exc),
                                       duration=self._elapsed()))
            return

        collected: list[str] = []
        assert self._proc.stdout is not None
        for line in self._proc.stdout:
            line = line.rstrip("\n")
            collected.append(line)
            self._lines.put(line)
            if self._on_line is not None:
                try:
                    self._on_line(line)
                except Exception:  # a bad callback must not kill the worker
                    log.exception("on_line callback raised")

        self._proc.wait()
        # Close the pipe explicitly; otherwise the fd lingers until GC and
        # repeated scans leak file descriptors (ResourceWarning).
        try:
            self._proc.stdout.close()
        except Exception:
            pass
        self._finish(CommandResult(
            self.command,
            returncode=self._proc.returncode,
            stdout="\n".join(collected),
            duration=self._elapsed(),
            cancelled=self._cancelled,
        ))

    def _finish(self, result: CommandResult) -> None:
        self._result = result
        self._done.set()
        if self._on_done is not None:
            try:
                self._on_done(result)
            except Exception:
                log.exception("on_done callback raised")

    def drain_lines(self) -> list[str]:
        """Return (and clear) any output lines received since the last call."""
        out: list[str] = []
        try:
            while True:
                out.append(self._lines.get_nowait())
        except queue.Empty:
            pass
        return out

    @property
    def finished(self) -> bool:
        return self._done.is_set()

    @property
    def result(self) -> Optional[CommandResult]:
        return self._result

    def cancel(self) -> None:
        """Terminate the process; escalate to kill after a short grace period."""
        self._cancelled = True
        proc = self._proc
        if proc is None or proc.poll() is not None:
            return
        try:
            proc.terminate()
        except Exception:
            pass

        def _escalate() -> None:
            try:
                proc.wait(timeout=1.0)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

        threading.Thread(target=_escalate, daemon=True).start()


class CommandRunner:
    """Factory + registry for command execution.

    Keeps track of running async commands so :meth:`shutdown` can cancel them
    all on exit, leaving no orphaned subprocesses.
    """

    def __init__(self) -> None:
        self._active: list[AsyncCommand] = []
        self._lock = threading.Lock()

    def run(self, command: Command, timeout: Optional[float] = None) -> CommandResult:
        cmd = list(command)
        start = time.monotonic()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return CommandResult(cmd, proc.returncode, proc.stdout, proc.stderr,
                                 time.monotonic() - start)
        except FileNotFoundError:
            return CommandResult(cmd, error="not found", duration=time.monotonic() - start)
        except subprocess.TimeoutExpired as exc:
            return CommandResult(cmd, timed_out=True,
                                 stdout=exc.stdout or "", stderr=exc.stderr or "",
                                 duration=time.monotonic() - start)
        except OSError as exc:
            return CommandResult(cmd, error=str(exc), duration=time.monotonic() - start)

    def run_async(self, command: Command, on_line: Optional[LineCallback] = None,
                  on_done: Optional[DoneCallback] = None) -> AsyncCommand:
        def _done(result: CommandResult) -> None:
            with self._lock:
                if task in self._active:
                    self._active.remove(task)
            if on_done is not None:
                on_done(result)

        task = AsyncCommand(command, on_line=on_line, on_done=_done)
        with self._lock:
            self._active.append(task)
        task.start()
        return task

    def shutdown(self) -> None:
        with self._lock:
            active = list(self._active)
        for task in active:
            task.cancel()
