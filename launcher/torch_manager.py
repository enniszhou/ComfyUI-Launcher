"""PyTorch version management."""
import subprocess


def get_installed_torch(python_exe: str) -> dict:
    """Get currently installed PyTorch version info."""
    script = """
import json
try:
    import torch
    info = {
        'version': torch.__version__,
        'cuda': torch.version.cuda,
        'hip': torch.version.hip,
    }
    print(json.dumps(info))
except ImportError:
    print(json.dumps(None))
"""
    try:
        result = subprocess.run(
            [python_exe, "-c", script],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return json.loads(result.stdout.strip())
    except Exception:
        pass
    return None


def install_torch(python_exe: str, install_cmd: str, callback=None) -> bool:
    """Install PyTorch using the given pip command."""
    try:
        cmd = [python_exe, "-m"] + install_cmd.split()
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        for line in process.stdout:
            if callback:
                callback(line.strip())
        process.wait()
        return process.returncode == 0
    except Exception as e:
        if callback:
            callback(f"Error: {e}")
        return False


def uninstall_torch(python_exe: str, callback=None) -> bool:
    """Uninstall current PyTorch."""
    return install_torch(python_exe, "pip uninstall -y torch torchvision torchaudio", callback)
