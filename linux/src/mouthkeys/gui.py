"""Optional Qt desktop controller. The daemon owns audio and never opens windows."""

import sys
from dataclasses import asdict
from datetime import datetime

from PySide6.QtCore import QProcess, Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .config import Config
from .service import ensure_daemon, request


class Request(QThread):
    done = Signal(object)

    def __init__(self, action, data=None, parent=None):
        super().__init__(parent)
        self.action, self.data = action, data or {}

    def run(self):
        try:
            self.done.emit({"result": request(self.action, **self.data)})
        except Exception as exc:
            self.done.emit({"error": str(exc)})


class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MouthKeys")
        self.resize(660, 560)
        self.jobs = set()
        self.polling = False
        self.rows = []
        self.download = None
        layout = QVBoxLayout(self)
        title = QLabel("MOUTHKEYS  /  LINUX")
        title.setStyleSheet("font-size: 22px; font-weight: bold")
        layout.addWidget(title)
        layout.addWidget(QLabel("LOCAL VOICE → TEXT"))
        self.status = QLabel("Ready")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color: #ff4f1f; padding: 12px 0")
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        self.toggle = QPushButton("Record / Stop")
        self.toggle.clicked.connect(lambda: self.send("toggle"))
        buttons.addWidget(self.toggle)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(lambda: self.send("cancel"))
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        hint = QLabel(
            "Bind a desktop shortcut to mouthkeys toggle to dictate without moving focus.\n"
            "On Wayland, finish speaking, then paste with Ctrl+V (Ctrl+Shift+V in terminals)."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        history = QWidget()
        history_layout = QVBoxLayout(history)
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self.select)
        history_layout.addWidget(self.list)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        history_layout.addWidget(self.preview)
        row = QHBoxLayout()
        for text, action in (("Copy", "copy"), ("Reprocess audio", "reprocess")):
            button = QPushButton(text)
            button.clicked.connect(
                lambda checked=False, action=action: self.selected_action(action)
            )
            row.addWidget(button)
        clear = QPushButton("Clear history")
        clear.clicked.connect(self.clear_history)
        row.addWidget(clear)
        history_layout.addLayout(row)
        tabs.addTab(history, "History")
        settings = QWidget()
        form = QFormLayout(settings)
        self.fields = {}
        config = asdict(Config.load())
        choices = {
            "device": ["cpu", "cuda", "auto"],
            "delivery": ["clipboard", "x11"],
            "paste_backend": ["auto", "xdotool", "wtype", "ydotool"],
            "paste_shortcut": ["ctrl+shift+v", "ctrl+v"],
        }
        for key in config:
            if key in choices:
                field = QComboBox()
                field.addItems(choices[key])
                field.setCurrentText(str(config[key]))
            else:
                field = QLineEdit(str(config[key]))
            self.fields[key] = field
            form.addRow(key.replace("_", " ").capitalize(), field)
        save = QPushButton("Save settings")
        save.clicked.connect(self.save)
        form.addRow(save)
        self.download_button = QPushButton("Download selected model")
        self.download_button.clicked.connect(self.download_model)
        form.addRow(self.download_button)
        warm = QPushButton("Load model into memory")
        warm.clicked.connect(lambda: self.send("warmup"))
        form.addRow(warm)
        tabs.addTab(settings, "Settings")
        self.setStyleSheet(
            "QWidget { background: #f5f3ed; color: #171717; font-family: monospace; }"
            "QPushButton { padding: 7px; border: 1px solid #777; }"
            "QPushButton:disabled { color: #888; }"
            "QLineEdit, QTextEdit, QListWidget { background: #fffdf7; }"
        )
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(700)
        self.poll()

    def send(self, action, data=None, callback=None):
        job = Request(action, data, self)
        self.jobs.add(job)

        def done(response):
            if "error" in response:
                self.status.setText(response["error"])
            if callback:
                callback(response)

        job.done.connect(done)
        job.finished.connect(lambda: self.jobs.discard(job))
        job.finished.connect(job.deleteLater)
        job.start()

    def poll(self):
        if self.polling:
            return
        self.polling = True

        def update(response):
            self.polling = False
            if "result" in response:
                result = response["result"]
                seconds = f"  {result['seconds']:.1f}s" if result["phase"] == "recording" else ""
                self.status.setText(f"{result['phase'].upper()}{seconds} · {result['message']}")
                self.toggle.setEnabled(result["phase"] in ("idle", "recording"))
                self.send("history", callback=self.update_history)

        self.send("status", callback=update)

    def update_history(self, response):
        if "result" not in response or response["result"] == self.rows:
            return
        selected = self.list.currentRow()
        selected_id = self.rows[selected]["id"] if 0 <= selected < len(self.rows) else None
        self.rows = response["result"]
        self.list.clear()
        for row in self.rows:
            date = datetime.fromtimestamp(row["created"]).strftime("%m-%d %H:%M")
            label = f"{date}  {row['status']}  {row['text'][:65] or row['error'][:65]}"
            self.list.addItem(QListWidgetItem(label))
        index = next((i for i, row in enumerate(self.rows) if row["id"] == selected_id), 0)
        self.list.setCurrentRow(index if self.rows else -1)

    def select(self, index):
        if 0 <= index < len(self.rows):
            row = self.rows[index]
            self.preview.setPlainText(row["text"] + (f"\n\n{row['error']}" if row["error"] else ""))
        else:
            self.preview.clear()

    def selected_action(self, action):
        index = self.list.currentRow()
        if 0 <= index < len(self.rows):
            self.send(action, {"id": self.rows[index]["id"]})

    def clear_history(self):
        if (
            QMessageBox.question(
                self, "Clear history", "Delete all transcripts and retained audio?"
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.send("clear")

    def save(self):
        try:
            values = {
                key: field.currentText() if isinstance(field, QComboBox) else field.text()
                for key, field in self.fields.items()
            }
            values["max_seconds"] = int(values["max_seconds"])
            Config(**values).save()
            self.status.setText("Saved; settings apply to the next recording")
            return True
        except Exception as exc:
            self.status.setText(str(exc))
            return False

    def download_model(self):
        if not self.save() or self.download is not None:
            return
        self.download = QProcess(self)
        self.download.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.download.setProgram(sys.executable)
        self.download.setArguments(["-m", "mouthkeys", "download"])
        self.download_button.setEnabled(False)
        self.download_button.setText("Downloading…")

        def finished(code, _):
            output = bytes(self.download.readAllStandardOutput()).decode(errors="replace")
            self.download.deleteLater()
            self.download = None
            self.download_button.setEnabled(True)
            self.download_button.setText("Download selected model")
            QMessageBox.information(self, "Model download", "Model ready" if code == 0 else output)

        self.download.finished.connect(finished)
        self.download.start()

    def closeEvent(self, event):
        if self.jobs or self.download is not None:
            self.status.setText("Wait for the current operation before closing")
            event.ignore()
            return
        event.accept()  # Closing the controller leaves the shortcut daemon running.


def launch():
    ensure_daemon()
    app = QApplication(sys.argv)
    app.setApplicationName("MouthKeys")
    window = Window()
    window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    window.show()
    return app.exec()
