"""QThread-based async workers."""
from PyQt6.QtCore import QThread, pyqtSignal

from .gpu_detector import detect_gpu
from .torch_manager import install_torch, uninstall_torch, get_installed_torch
from .utils import run_command_streaming


class BaseWorker(QThread):
    output = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    @property
    def cancelled(self):
        return self._cancelled


class DetectWorker(BaseWorker):
    result = pyqtSignal(dict)

    def __init__(self, python_exe, parent=None):
        super().__init__(parent)
        self.python_exe = python_exe

    def run(self):
        info = detect_gpu(self.python_exe)
        self.result.emit(info)
        self.finished.emit(True, "Detection complete")


class PipWorker(BaseWorker):

    def __init__(self, python_exe, command, parent=None):
        super().__init__(parent)
        self.python_exe = python_exe
        self.command = command

    def run(self):
        if self.command.startswith("uninstall"):
            success = uninstall_torch(self.python_exe, callback=self.output.emit)
        else:
            success = install_torch(self.python_exe, self.command, callback=self.output.emit)
        if success:
            self.finished.emit(True, "Operation completed")
        else:
            self.finished.emit(False, "Operation failed")


class GitWorker(BaseWorker):

    def __init__(self, git_exe, cwd, args, parent=None):
        super().__init__(parent)
        self.git_exe = git_exe
        self.cwd = cwd
        self.args = args

    def run(self):
        cmd = [self.git_exe] + self.args
        rc = run_command_streaming(cmd, cwd=self.cwd, callback=self.output.emit)
        if rc == 0:
            self.finished.emit(True, "Git operation completed")
        else:
            self.finished.emit(False, f"Git exited with code {rc}")


class ExtensionWorker(BaseWorker):

    def __init__(self, git_exe, comfyui_dir, action, ext_name=None, ext_url=None, parent=None):
        super().__init__(parent)
        self.git_exe = git_exe
        self.comfyui_dir = comfyui_dir
        self.action = action
        self.ext_name = ext_name
        self.ext_url = ext_url

    def run(self):
        import os
        ext_dir = os.path.join(self.comfyui_dir, "custom_nodes")
        os.makedirs(ext_dir, exist_ok=True)

        if self.action == "install" and self.ext_url:
            name = self.ext_name or self.ext_url.rstrip("/").split("/")[-1]
            if name.endswith(".git"):
                name = name[:-4]
            target = os.path.join(ext_dir, name)
            if os.path.exists(target):
                self.output.emit(f"Extension '{name}' already exists")
                self.finished.emit(False, "Extension already exists")
                return
            cmd = [self.git_exe, "clone", self.ext_url, target]
            rc = run_command_streaming(cmd, callback=self.output.emit)
            if rc == 0:
                self.finished.emit(True, f"Installed '{name}'")
            else:
                self.finished.emit(False, "Clone failed")

        elif self.action == "update" and self.ext_name:
            target = os.path.join(ext_dir, self.ext_name)
            if not os.path.exists(target):
                self.finished.emit(False, f"'{self.ext_name}' not found")
                return
            cmd = [self.git_exe, "-C", target, "pull"]
            rc = run_command_streaming(cmd, callback=self.output.emit)
            if rc == 0:
                self.finished.emit(True, f"Updated '{self.ext_name}'")
            else:
                self.finished.emit(False, "Update failed")

        elif self.action == "remove" and self.ext_name:
            import shutil
            target = os.path.join(ext_dir, self.ext_name)
            if not os.path.exists(target):
                self.finished.emit(False, f"'{self.ext_name}' not found")
                return
            try:
                shutil.rmtree(target)
                self.output.emit(f"Removed '{self.ext_name}'")
                self.finished.emit(True, f"Removed '{self.ext_name}'")
            except Exception as e:
                self.finished.emit(False, str(e))

        elif self.action == "update_all":
            import os as _os
            dirs = []
            if os.path.isdir(ext_dir):
                dirs = [d for d in os.listdir(ext_dir)
                        if os.path.isdir(os.path.join(ext_dir, d)) and os.path.isdir(os.path.join(ext_dir, d, ".git"))]
            all_ok = True
            for d in dirs:
                if self.cancelled:
                    break
                target = os.path.join(ext_dir, d)
                self.output.emit(f"Updating {d}...")
                cmd = [self.git_exe, "-C", target, "pull"]
                rc = run_command_streaming(cmd, callback=self.output.emit)
                if rc != 0:
                    all_ok = False
            self.finished.emit(all_ok, "Update all completed")
        else:
            self.finished.emit(False, "Unknown action")
