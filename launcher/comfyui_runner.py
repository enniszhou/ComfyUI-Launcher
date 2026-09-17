"""ComfyUI process runner with non-blocking output."""
import subprocess
import os
import threading
from PyQt6.QtCore import QObject, pyqtSignal, QThread


class OutputReader(QThread):
    """Thread to read process output without blocking UI."""
    line_received = pyqtSignal(str)
    process_exited = pyqtSignal(int)

    def __init__(self, process, parent=None):
        super().__init__(parent)
        self.process = process
        self._running = True

    def run(self):
        try:
            while self._running and self.process.poll() is None:
                line = self.process.stdout.readline()
                if line:
                    self.line_received.emit(line.rstrip())
                else:
                    if self.process.poll() is not None:
                        break
        except Exception:
            pass

        rc = self.process.returncode if self.process.returncode is not None else -1
        self.process_exited.emit(rc)

    def stop(self):
        self._running = False


class ComfyUIRunner(QObject):
    started = pyqtSignal(int)
    output_line = pyqtSignal(str)
    finished = pyqtSignal(int)

    def __init__(self, comfyui_dir: str, python_exe: str, parent=None):
        super().__init__(parent)
        self.comfyui_dir = comfyui_dir
        self.python_exe = python_exe
        self.process = None
        self.reader_thread = None

    def start(self, port: int = 8188, listen: bool = True, extra_args: list = None) -> bool:
        if self.process and self.process.poll() is None:
            return False

        cmd = [self.python_exe, "main.py", "--port", str(port)]
        if listen:
            cmd.append("--listen")
        if extra_args:
            cmd.extend(extra_args)
        
        print(f"[DEBUG] Starting ComfyUI with command: {' '.join(cmd)}")

        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=self.comfyui_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self.started.emit(self.process.pid)

            self.reader_thread = OutputReader(self.process)
            self.reader_thread.line_received.connect(self.output_line.emit)
            self.reader_thread.process_exited.connect(self.finished.emit)
            self.reader_thread.start()

            return True
        except Exception as e:
            print(f"Failed to start: {e}")
            return False

    def stop(self):
        if self.process and self.process.poll() is None:
            if self.reader_thread:
                self.reader_thread.stop()
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None
        self.reader_thread = None

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None
