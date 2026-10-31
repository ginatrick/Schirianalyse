"""Logging that the CLI prints and the web UI can follow (per thread)."""
from __future__ import annotations

import threading
import time

_local = threading.local()


def set_sink(fn) -> None:
    """fn(line: str) receives every log line of the current thread; None to stop."""
    _local.fn = fn


def set_step(fn) -> None:
    """fn(step: str) is told which pipeline step starts."""
    _local.step = fn


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    fn = getattr(_local, "fn", None)
    if fn:
        fn(line)


def step(name: str) -> None:
    fn = getattr(_local, "step", None)
    if fn:
        fn(name)
