"""Logging that the CLI prints and the web UI can follow (per thread)."""
from __future__ import annotations

import threading
import time

_local = threading.local()


class Cancelled(BaseException):
    """Raised inside a job when the user pressed "Abbrechen".
    BaseException so that generic `except Exception` blocks don't swallow it."""


def set_cancel(event: threading.Event | None) -> None:
    _local.cancel = event


def check_cancel() -> None:
    ev = getattr(_local, "cancel", None)
    if ev is not None and ev.is_set():
        raise Cancelled()


def cancel_event() -> threading.Event | None:
    return getattr(_local, "cancel", None)


def sleep(seconds: float) -> None:
    """time.sleep that ends early (with Cancelled) when the job is cancelled."""
    ev = getattr(_local, "cancel", None)
    if ev is None:
        time.sleep(seconds)
    elif ev.wait(seconds):
        raise Cancelled()


def run_cancellable(fn):
    """Run a blocking call (e.g. an HTTP request) so that cancelling does not wait for it.
    The call itself keeps running in the background and its result is dropped."""
    ev = getattr(_local, "cancel", None)
    if ev is None:
        return fn()
    box: dict = {}

    def target():
        try:
            box["ok"] = fn()
        except BaseException as e:
            box["err"] = e

    t = threading.Thread(target=target, daemon=True)
    t.start()
    while t.is_alive():
        t.join(0.5)
        if ev.is_set():
            raise Cancelled()
    if "err" in box:
        raise box["err"]
    return box.get("ok")


def set_sink(fn) -> None:
    """fn(line: str) receives every log line of the current thread; None to stop."""
    _local.fn = fn


def set_step(fn) -> None:
    """fn(step: str) is told which pipeline step starts."""
    _local.step = fn


def log(msg: str) -> None:
    check_cancel()
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    fn = getattr(_local, "fn", None)
    if fn:
        fn(line)


def step(name: str) -> None:
    check_cancel()
    fn = getattr(_local, "step", None)
    if fn:
        fn(name)
