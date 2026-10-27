from dataclasses import replace
from types import SimpleNamespace

import pytest

from mouthkeys import delivery
from mouthkeys.config import Config


@pytest.mark.parametrize("desktop", ["x11", "wayland"])
def test_copy_unicode_uses_stdin_not_shell(monkeypatch, desktop):
    monkeypatch.setattr(delivery, "session", lambda: desktop)
    calls = []

    def run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(stdout=b"")

    monkeypatch.setattr(delivery, "run", run)
    monkeypatch.setattr(delivery.subprocess, "run", run)
    text = '日本語 café\n$(touch /tmp/never) "hello"'
    delivery.Delivery().copy(text)
    args, kwargs = calls[0]
    assert text not in args
    assert kwargs["input"] == text.encode()
    assert not kwargs.get("shell")


@pytest.mark.parametrize(
    "focuses,target,expected",
    [
        (["10", "10"], "10", "paste_requested"),
        (["20"], "10", "copied"),
        (["10", "20"], "10", "copied"),
        ([], None, "copied"),
    ],
)
def test_x11_focus_guard(monkeypatch, focuses, target, expected):
    monkeypatch.setattr(delivery, "session", lambda: "x11")
    monkeypatch.setattr(delivery.time, "sleep", lambda _: None)
    adapter = delivery.Delivery()
    calls = []
    focus = iter(focuses)
    monkeypatch.setattr(adapter, "focus", lambda: next(focus))
    monkeypatch.setattr(adapter, "copy", lambda text: calls.append("copy"))
    monkeypatch.setattr(adapter, "paste_key", lambda _: calls.append("paste"))
    assert adapter.deliver("hello", Config(delivery="x11"), target) == expected
    assert calls == (["copy", "paste"] if expected == "paste_requested" else ["copy"])


def test_wayland_never_auto_pastes_even_with_xwayland_display(monkeypatch):
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    assert delivery.session() == "wayland"
    adapter = delivery.Delivery()
    calls = []
    monkeypatch.setattr(adapter, "copy", lambda _: calls.append("copy"))
    monkeypatch.setattr(adapter, "paste_key", lambda _: pytest.fail("Unexpected auto paste"))
    assert adapter.deliver("hello", Config(delivery="x11"), "123") == "copied"
    assert calls == ["copy"]


@pytest.mark.parametrize(
    "backend,expected",
    [
        ("xdotool", ["xdotool", "key", "--clearmodifiers", "ctrl+shift+v"]),
        ("wtype", ["wtype", "-M", "ctrl", "-M", "shift", "-k", "v", "-m", "shift", "-m", "ctrl"]),
        ("ydotool", ["ydotool", "key", "29:1", "42:1", "47:1", "47:0", "42:0", "29:0"]),
    ],
)
def test_terminal_paste_chords_release_modifiers(monkeypatch, backend, expected):
    monkeypatch.setattr(delivery, "session", lambda: "x11")
    calls = []
    monkeypatch.setattr(delivery, "run", lambda args: calls.append(args))
    delivery.Delivery().paste_key(replace(Config(), paste_backend=backend))
    assert calls == [expected]


def test_wayland_auto_backend_requires_explicit_configuration(monkeypatch):
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    with pytest.raises(ValueError, match="Wayland"):
        delivery.Delivery().paste_key(Config())


def test_headless_never_changes_clipboard():
    with pytest.raises(RuntimeError, match="No desktop"):
        delivery.Delivery().copy("hello")
