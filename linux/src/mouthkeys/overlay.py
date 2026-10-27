"""Datasheet Mono recording panel; independent of the settings window."""

import fcntl
import os
import socket
import subprocess
import sys
import time

from PySide6.QtCore import QRect, QRectF, QSize, QSocketNotifier, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QFont, QIcon, QPainter, QPen, QPixmap, QTextLayout
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from .config import Config, runtime_dir
from .gui import Request
from .processes import python_command
from .trace import Trace


def button_icon(action, color):
    """Small vector marks, independent of installed symbol fonts."""
    pixmap = QPixmap(20, 20)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(color), 1.5))
    if action == "copy":
        painter.drawRect(4, 3, 10, 11)
        painter.drawRect(7, 6, 10, 11)
    elif action == "history":
        for y in (5, 10, 15):
            painter.drawLine(4, y, 16, y)
    elif action == "cancel":
        painter.drawLine(5, 5, 15, 15)
        painter.drawLine(5, 15, 15, 5)
    else:
        painter.drawArc(4, 4, 12, 12, 35 * 16, 290 * 16)
        painter.drawLine(16, 3, 16, 8)
        painter.drawLine(16, 8, 11, 8)
    painter.end()
    return QIcon(pixmap)


class Overlay(QWidget):
    """340 × 130 pill and 30 px rails, matching the native round-six geometry."""

    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(424, 146)
        self.data = {}
        self.trace = Trace()
        self.meter_frame = None
        self.text_cache = None
        self.jobs = set()
        self.pending = False
        self.active = False
        self.dismiss_at = None
        self.positioned = False
        self.drag = None
        self.seconds = 0
        self.notice = None
        self.notice_serial = None
        self.failures = 0
        self.buttons = {}
        for action, tip, x, y in (
            ("history", "Open history", 6, 29),
            ("copy", "Copy transcript", 6, 83),
            ("cancel", "Cancel / dismiss", 388, 29),
            ("reprocess", "Reprocess retained audio", 388, 83),
        ):
            button = QPushButton(self)
            button.setIconSize(QSize(20, 20))
            button.setGeometry(x, y, 30, 30)
            button.setToolTip(tip)
            button.setAccessibleName(tip)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.clicked.connect(lambda checked=False, action=action: self.action(action))
            self.buttons[action] = button
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(200)
        self.animation = QTimer(self)
        self.animation.setTimerType(Qt.TimerType.PreciseTimer)
        self.animation.timeout.connect(self.animate)
        self.apply_theme()
        QApplication.styleHints().colorSchemeChanged.connect(self.apply_theme)

    def apply_theme(self, *_):
        light = QApplication.styleHints().colorScheme() == Qt.ColorScheme.Light
        self.surface = "#ffffff" if light else "#111214"
        self.ink = "#111214" if light else "#ebebec"
        self.edge = "#111214" if light else "#2c2e33"
        self.dim = "#55565a" if light else "#949597"
        chip = "#f2f2f4" if light else "#1a1b1f"
        self.setStyleSheet(
            f"QPushButton {{ background: {chip}; color: {self.ink}; border: none;"
            "font-size: 20px; border-radius: 0; }"
            f"QPushButton:hover {{ border: 1px solid {self.ink}; }}"
            f"QPushButton:pressed {{ background: {self.ink}; color: {self.surface}; }}"
            f"QPushButton:disabled {{ color: {self.dim}; }}"
        )
        for action, button in self.buttons.items():
            button.setIcon(button_icon(action, self.ink))
        self.update()

    def send(self, action, callback=None):
        data = (
            {"id": self.data["id"]}
            if action in ("copy", "reprocess") and self.data.get("id")
            else {}
        )
        job = Request(action, data, parent=self)
        self.jobs.add(job)
        if callback:
            job.done.connect(callback)
        else:

            def feedback(response):
                if "error" in response:
                    self.notice = (response["error"], time.monotonic() + 10)
                    self.dismiss_at = self.notice[1]
                    self.show()
                    self.update()

            job.done.connect(feedback)
        job.finished.connect(lambda: self.jobs.discard(job))
        job.finished.connect(job.deleteLater)
        job.start()

    def action(self, action):
        if action == "history":
            subprocess.Popen(python_command("mouthkeys", "gui"), start_new_session=True)
        elif action == "cancel":
            if self.active:
                self.send("cancel")
            self.hide()
            self.dismiss_at = 0
        else:
            self.send(action)

    def poll(self):
        if self.pending:
            return
        self.pending = True

        def received(response):
            self.pending = False
            if "result" in response:
                self.failures = 0
                self.timer.setInterval(50 if response["result"]["phase"] == "recording" else 200)
                self.set_status(response["result"])
            else:
                self.hide()  # Shutdown/disconnect must not leave a stale recording panel.
                self.active = False
                self.notice_serial = None
                self.animation.stop()
                self.failures += 1
                self.timer.setInterval(min(5000, 200 * 2 ** min(self.failures, 5)))

        self.send("status", received)

    def place(self):
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        self.move(area.center().x() - self.width() // 2, area.bottom() - self.height() - 50)
        self.positioned = True

    def set_status(self, data):
        if Config.load().recording_panel == "off":
            self.hide()
            self.active = False
            self.notice_serial = None
            return
        active = data["phase"] in ("recording", "stopping", "transcribing", "delivering", "loading")
        new_recording = data.get("id") != self.data.get("id")
        if active and (not self.active or new_recording):
            self.dismiss_at = None
            self.notice = None
            if not self.positioned:
                self.place()
            self.show()  # Never activate or raise the destination app.
        if not active and self.active:
            message = data.get("message", "")
            success = message.startswith(("Copied —", "Paste requested —"))
            self.dismiss_at = time.monotonic() + (0.6 if success else 10)
            if message == "Cancelled":
                self.dismiss_at = 0
        notice = data.get("notice")
        if not notice:
            self.notice = None
            self.notice_serial = None
        if notice and notice["serial"] != self.notice_serial:
            self.notice_serial = notice["serial"]
            if time.time() - notice["at"] < 10:
                self.notice = (notice["message"], time.monotonic() + 10)
                self.dismiss_at = self.notice[1]
                if not self.positioned:
                    self.place()
                self.show()
        if self.dismiss_at is not None and time.monotonic() >= self.dismiss_at:
            self.hide()
        now = time.monotonic()
        if data["phase"] == "recording":
            if new_recording or self.data.get("phase") != "recording":
                self.trace.begin(now)
                self.meter_frame = None
            meter = data.get("meter", {})
            if meter.get("frame") is not None and meter["frame"] != self.meter_frame:
                self.trace.ingest(meter["level"], min(now, meter["at"]))
                self.meter_frame = meter["frame"]
        else:
            self.trace.stop(now)
        if active and not self.animation.isActive():
            self.animation.start(16)
        self.active = active
        self.data = data
        if data["phase"] == "recording":
            self.seconds = data.get("seconds", 0)
        self.buttons["copy"].setEnabled(not active and bool(data.get("preview")))
        self.buttons["reprocess"].setEnabled(not active)
        self.update()

    def animate(self):
        if not self.isVisible():
            self.animation.stop()
            return
        now = time.monotonic()
        self.trace.advance(now)
        self.update(QRect(53, 68, 252, 40))
        if (
            self.data.get("phase") == "idle"
            and self.trace.stopped_at is not None
            and now - self.trace.stopped_at >= 0.06
        ):
            self.animation.stop()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(42, 8, 340, 130, QColor(0, 0, 0, 80))
        p.fillRect(42, 6, 340, 130, QColor(self.surface))
        p.setPen(QColor(self.edge))
        p.drawRect(42, 6, 339, 129)
        phase = self.data.get("phase", "idle")
        text = self.data.get("preview", "")
        if phase == "idle":
            text = self.data.get("message", "Ready")
        elif phase != "recording":
            text = self.data.get("message", "Working…")
        elif not text:
            text = "Listening…"
        if self.notice and time.monotonic() < self.notice[1]:
            text = self.notice[0]
        # Lay out prose into three 16 px lines, keeping the newest words in view.
        font = QFont("sans-serif")
        font.setPixelSize(13)
        if self.text_cache is None or self.text_cache[0] != text:
            layout = QTextLayout(text, font)
            layout.beginLayout()
            lines = []
            while True:
                line = layout.createLine()
                if not line.isValid():
                    break
                line.setLineWidth(316)
                lines.append(text[line.textStart() : line.textStart() + line.textLength()])
            layout.endLayout()
            self.text_cache = (text, lines[-3:])
        p.setFont(font)
        p.setPen(QColor(self.dim if phase == "transcribing" else self.ink))
        for i, part in enumerate(self.text_cache[1]):
            p.drawText(54, 28 + i * 16, part)
        p.setPen(QColor(self.edge))
        p.drawLine(54, 87, 304, 87)
        p.setPen(Qt.PenStyle.NoPen)
        p.save()
        p.setClipRect(QRectF(54, 70, 250, 34))
        scale = self.devicePixelRatioF()
        for i, height in enumerate(self.trace.shown):
            x = round((54 + i * 4 - self.trace.fraction * 4) * scale) / scale
            top = round((87 - height / 2) * scale) / scale
            bottom = round((87 + height / 2) * scale) / scale
            p.fillRect(QRectF(x, top, 2, bottom - top), QColor(self.ink))
        p.restore()
        if phase == "transcribing":
            x = 54 + (int(time.monotonic() / (1.05 / 55)) % 55) * 4
            p.fillRect(x, 85, 24, 4, QColor("#ff4f1f"))
        p.setPen(QColor("#ff4f1f"))
        if phase == "recording":
            p.fillRect(316, 84, 6, 6, QColor("#ff4f1f"))
        else:
            p.drawRect(316, 84, 5, 5)
        mono = QFont("monospace")
        mono.setPixelSize(14)
        p.setFont(mono)
        p.setPen(QColor(self.ink))
        seconds = int(self.seconds)
        p.drawText(326, 92, f"{seconds // 60}:{seconds % 60:02d}")
        mono.setPixelSize(10)
        p.setFont(mono)
        p.setPen(QColor(self.dim))
        p.drawText(54, 124, "LIVE PREVIEW" if active_phase(phase) else "MOUTHKEYS")
        mic = self.data.get("microphone", "DEFAULT").upper()
        p.drawText(190, 124, p.fontMetrics().elidedText(mic, Qt.TextElideMode.ElideRight, 100))
        p.drawText(302, 124, "LOCAL")
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if self.drag is not None:
            self.move(event.globalPosition().toPoint() - self.drag)

    def mouseReleaseEvent(self, event):
        self.drag = None

    def mouseDoubleClickEvent(self, event):
        self.place()


def active_phase(phase):
    return phase in ("recording", "stopping", "transcribing", "delivering", "loading")


def launch():
    # A separate lifetime means closing Settings never removes shortcut feedback.
    with (runtime_dir() / "overlay.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        app = QApplication(sys.argv)
        app.setApplicationName("MouthKeys")
        app.setQuitOnLastWindowClosed(False)
        panel = Overlay()
        # Wake a resident panel immediately when a shortcut restarts the daemon.
        path = runtime_dir() / "overlay-wake.sock"
        path.unlink(missing_ok=True)
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as wake:
            wake.bind(str(path))
            os.chmod(path, 0o600)
            wake.setblocking(False)
            notifier = QSocketNotifier(wake.fileno(), QSocketNotifier.Type.Read)

            def awakened(*_):
                try:
                    while wake.recv(64):
                        pass
                except BlockingIOError:
                    pass
                panel.timer.setInterval(200)
                panel.poll()

            notifier.activated.connect(awakened)
            panel.poll()
            try:
                return app.exec()
            finally:
                notifier.setEnabled(False)
                path.unlink(missing_ok=True)
