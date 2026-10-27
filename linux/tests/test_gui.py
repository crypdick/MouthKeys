import time

import pytest

pytest.importorskip("PySide6")


def test_offscreen_controller_renders_history_and_saves_settings(monkeypatch):
    from PySide6.QtWidgets import QApplication

    from mouthkeys import gui
    from mouthkeys.config import Config

    app = QApplication.instance() or QApplication([])

    def request(action, **data):
        if action == "status":
            return {"phase": "idle", "message": "Ready", "seconds": 0}
        if action == "history":
            return [
                {
                    "id": "example",
                    "created": 1,
                    "status": "copied",
                    "text": "Hello café",
                    "error": "",
                }
            ]
        raise AssertionError(f"Unexpected GUI request: {action}")

    monkeypatch.setattr(gui, "request", request)
    window = gui.Window()
    window.timer.stop()
    deadline = time.monotonic() + 3
    while (window.jobs or not window.rows) and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert not window.jobs
    assert window.preview.toPlainText() == "Hello café"
    window.fields["model"].setCurrentText("small.en")
    assert window.save()
    assert Config.load().model == "small.en"
    window.fields["language"].setCurrentIndex(window.fields["language"].findData("es"))
    window.fields["compute_type"].setCurrentIndex(window.fields["compute_type"].findData("auto"))
    window.fields["max_seconds"].setValue(120)
    assert window.save()
    saved = Config.load()
    assert (saved.language, saved.compute_type, saved.max_seconds) == ("es", "auto", 120)
    assert "Spanish" in window.fields["language"].currentText()
    window.fields["model"].setEditText("/custom/local model")
    window.fields["audio_source"].setEditText("my_microphone")
    assert window.save()
    assert Config.load().model == "/custom/local model"
    assert Config.load().audio_source == "my_microphone"
    assert not window.isVisible()  # No visible windows, even on the offscreen platform.
    window.close()


def test_dropdowns_preserve_existing_custom_settings(monkeypatch):
    from PySide6.QtWidgets import QApplication

    from mouthkeys import gui
    from mouthkeys.config import Config

    app = QApplication.instance() or QApplication([])
    Config(model="org/custom-model", language="xx", audio_source="custom_source").save()
    monkeypatch.setattr(gui.Window, "poll", lambda self: None)
    window = gui.Window()
    window.timer.stop()
    assert window.fields["model"].currentText() == "org/custom-model"
    assert window.fields["language"].currentData() == "xx"
    assert window.save()
    assert Config.load().model == "org/custom-model"
    assert Config.load().language == "xx"
    assert Config.load().audio_source == "custom_source"
    assert not window.isVisible()
    window.close()
    app.processEvents()


def test_microphone_choices_use_discovery_without_capture(monkeypatch):
    import subprocess

    from mouthkeys import delivery, gui

    monkeypatch.setattr(delivery, "session", lambda: "x11")

    def run(args, **kwargs):
        assert args == ["pactl", "list", "short", "sources"]
        assert kwargs["timeout"] == 2
        return subprocess.CompletedProcess(args, 0, "12\tmy_microphone\tdriver\tRUNNING\n")

    monkeypatch.setattr(subprocess, "run", run)
    assert gui.audio_sources() == ["default", "my_microphone"]


def test_missing_pactl_keeps_manual_microphone_selection(monkeypatch):
    import subprocess

    from mouthkeys import delivery, gui

    monkeypatch.setattr(delivery, "session", lambda: "x11")

    def run(*args, **kwargs):
        raise FileNotFoundError("pactl")

    monkeypatch.setattr(subprocess, "run", run)
    assert gui.audio_sources() == ["default"]
