"""Utility functions."""
import os
import sys
import subprocess
import json


def get_python_exe(comfyui_dir: str) -> str:
    """Find python executable relative to comfyui directory."""
    candidates = [
        os.path.join(comfyui_dir, "..", "python", "python.exe"),
        os.path.join(comfyui_dir, "..", "python", "python"),
        os.path.join(comfyui_dir, "python", "python.exe"),
        sys.executable,
    ]
    for c in candidates:
        p = os.path.normpath(c)
        if os.path.isfile(p):
            return p
    return sys.executable


def run_command(cmd: list, cwd: str = None, callback=None) -> tuple:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300, cwd=cwd
        )
        if callback:
            callback(result.stdout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def run_command_streaming(cmd: list, cwd: str = None, callback=None) -> int:
    """Run a command with streaming output."""
    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace', cwd=cwd
        )
        for line in process.stdout:
            if callback:
                callback(line.rstrip())
        process.wait()
        return process.returncode
    except Exception as e:
        if callback:
            callback(f"Error: {e}")
        return -1


def load_json_file(path: str) -> dict:
    """Load a JSON file, return empty dict on failure."""
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_json_file(path: str, data: dict):
    """Save data to a JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
