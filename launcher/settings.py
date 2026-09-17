"""Settings management."""
import json
import os


DEFAULT_SETTINGS = {
    "comfyui_dir": "",
    "python_exe": "",
    "git_exe": "",
    "port": 8188,
    "listen": True,
    "gpu_type": "auto",
    "extra_args": "",
    "theme": "dark",
    "pip_mirror": "official",
    "hf_mirror": "official",
    "git_mirror": "official",
    "proxy_address": "",
    "proxy_enabled": False,
    "proxy_git": False,
    "proxy_pip": False,
    "proxy_hf": False,
    "disabled_patches": [],
    "window_width": 1100,
    "window_height": 750,
}


class Settings:
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
        self.config_path = os.path.abspath(config_path)
        self.settings = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                return {**DEFAULT_SETTINGS, **saved}
            except Exception:
                pass
        return DEFAULT_SETTINGS.copy()

    def save(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default=None):
        return self.settings.get(key, default)

    def set(self, key: str, value):
        self.settings[key] = value
        self.save()

    def update(self, data: dict):
        self.settings.update(data)
        self.save()

    @property
    def comfyui_dir(self) -> str:
        return self.settings.get("comfyui_dir", "")

    @comfyui_dir.setter
    def comfyui_dir(self, value: str):
        self.set("comfyui_dir", value)

    @property
    def python_exe(self) -> str:
        return self.settings.get("python_exe", "")

    @python_exe.setter
    def python_exe(self, value: str):
        self.set("python_exe", value)

    @property
    def git_exe(self) -> str:
        val = self.settings.get("git_exe", "")
        if not val:
            import shutil
            val = shutil.which("git") or "git"
        return val

    @git_exe.setter
    def git_exe(self, value: str):
        self.set("git_exe", value)

    @property
    def port(self) -> int:
        return self.settings.get("port", 8188)

    @port.setter
    def port(self, value: int):
        self.set("port", value)

    @property
    def listen(self) -> bool:
        return self.settings.get("listen", True)

    @listen.setter
    def listen(self, value: bool):
        self.set("listen", value)

    @property
    def extra_args(self) -> str:
        return self.settings.get("extra_args", "")

    @extra_args.setter
    def extra_args(self, value: str):
        self.set("extra_args", value)

    @property
    def theme(self) -> str:
        return self.settings.get("theme", "dark")

    @theme.setter
    def theme(self, value: str):
        self.set("theme", value)

    @property
    def pip_mirror(self) -> str:
        return self.settings.get("pip_mirror", "official")

    @pip_mirror.setter
    def pip_mirror(self, value: str):
        self.set("pip_mirror", value)

    @property
    def hf_mirror(self) -> str:
        return self.settings.get("hf_mirror", "official")

    @hf_mirror.setter
    def hf_mirror(self, value: str):
        self.set("hf_mirror", value)

    @property
    def proxy_address(self) -> str:
        return self.settings.get("proxy_address", "")

    @proxy_address.setter
    def proxy_address(self, value: str):
        self.set("proxy_address", value)

    @property
    def proxy_enabled(self) -> bool:
        return self.settings.get("proxy_enabled", False)

    @proxy_enabled.setter
    def proxy_enabled(self, value: bool):
        self.set("proxy_enabled", value)

    @property
    def proxy_git(self) -> bool:
        return self.settings.get("proxy_git", False)

    @proxy_git.setter
    def proxy_git(self, value: bool):
        self.set("proxy_git", value)

    @property
    def proxy_pip(self) -> bool:
        return self.settings.get("proxy_pip", False)

    @proxy_pip.setter
    def proxy_pip(self, value: bool):
        self.set("proxy_pip", value)

    @property
    def disabled_patches(self) -> list:
        return self.settings.get("disabled_patches", [])

    @disabled_patches.setter
    def disabled_patches(self, value: list):
        self.set("disabled_patches", value)
