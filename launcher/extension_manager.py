"""Extension management for ComfyUI custom nodes."""
import os
import json
from .utils import run_command


def get_extensions_dir(comfyui_dir: str) -> str:
    return os.path.join(comfyui_dir, "custom_nodes")


def list_extensions(comfyui_dir: str, git_exe: str = "git") -> list:
    ext_dir = get_extensions_dir(comfyui_dir)
    if not os.path.isdir(ext_dir):
        return []

    extensions = []
    for name in sorted(os.listdir(ext_dir)):
        path = os.path.join(ext_dir, name)
        if not os.path.isdir(path):
            continue

        disabled = name.endswith(".disabled")
        real_name = name.replace(".disabled", "") if disabled else name

        ext_info = {
            "name": real_name,
            "path": path,
            "disabled": disabled,
            "has_git": os.path.isdir(os.path.join(path, ".git")),
        }

        if ext_info["has_git"]:
            try:
                rc, out, _ = run_command(
                    [git_exe, "log", "--oneline", "-1"], cwd=path
                )
                if rc == 0 and out:
                    ext_info["version"] = out.strip()
            except Exception:
                pass

        js_path = os.path.join(path, "pyproject.toml")
        if not os.path.exists(js_path):
            js_path = os.path.join(path, "package.json")
        if os.path.exists(js_path):
            ext_info["has_config"] = True

        extensions.append(ext_info)

    return extensions


def install_extension(comfyui_dir: str, url: str, git_exe: str = "git") -> tuple:
    ext_dir = get_extensions_dir(comfyui_dir)
    os.makedirs(ext_dir, exist_ok=True)

    name = url.rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    target = os.path.join(ext_dir, name)

    if os.path.exists(target):
        return False, f"Extension '{name}' already exists"

    rc, out, err = run_command([git_exe, "clone", url, target])
    if rc == 0:
        return True, f"Installed '{name}'"
    return False, f"Clone failed: {err}"


def remove_extension(comfyui_dir: str, name: str) -> tuple:
    import shutil
    ext_dir = get_extensions_dir(comfyui_dir)
    target = os.path.join(ext_dir, name)
    if not os.path.exists(target):
        target_disabled = target + ".disabled"
        if os.path.exists(target_disabled):
            target = target_disabled
        else:
            return False, f"'{name}' not found"
    try:
        shutil.rmtree(target)
        return True, f"Removed '{name}'"
    except Exception as e:
        return False, str(e)


def toggle_extension(comfyui_dir: str, name: str) -> tuple:
    ext_dir = get_extensions_dir(comfyui_dir)
    enabled_path = os.path.join(ext_dir, name)
    disabled_path = enabled_path + ".disabled"

    if os.path.exists(enabled_path):
        os.rename(enabled_path, disabled_path)
        return True, f"Disabled '{name}'"
    elif os.path.exists(disabled_path):
        os.rename(disabled_path, enabled_path)
        return True, f"Enabled '{name}'"
    return False, f"'{name}' not found"


def update_extension(comfyui_dir: str, name: str, git_exe: str = "git") -> tuple:
    ext_dir = get_extensions_dir(comfyui_dir)
    target = os.path.join(ext_dir, name)
    if not os.path.exists(target):
        return False, f"'{name}' not found"
    rc, out, err = run_command([git_exe, "-C", target, "pull"])
    if rc == 0:
        return True, out.strip()
    return False, err.strip()


def fetch_online_list(url: str = None) -> list:
    if url is None:
        url = "https://extension-list.oystermercury.top"
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "ComfyUI-Launcher/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "extensions" in data:
                return data["extensions"]
    except Exception:
        pass
    return []
