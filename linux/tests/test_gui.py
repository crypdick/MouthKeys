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
    window.fields["model"].setText("small.en")
    assert window.save()
    assert Config.load().model == "small.en"
    assert not window.isVisible()  # No visible windows, even on the offscreen platform.
    window.close()
