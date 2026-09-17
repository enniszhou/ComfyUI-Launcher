"""GPU detection module."""
import json
import subprocess


class GPUType:
    NVIDIA = "nvidia"
    AMD = "amd"
    INTEL = "intel"
    CPU = "cpu"
    UNKNOWN = "unknown"


def detect_gpu(python_exe: str) -> dict:
    """Detect GPU type and info using the specified Python executable."""
    script = """
import json, sys
try:
    import torch
    info = {
        'torch_version': torch.__version__,
        'cuda_version': torch.version.cuda,
        'hip_version': torch.version.hip,
        'cuda_available': torch.cuda.is_available(),
        'device_count': torch.cuda.device_count() if torch.cuda.is_available() else 0,
    }
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        info['device_name'] = props.name
        info['total_memory_gb'] = round(props.total_memory / 1024**3, 1)
        if hasattr(props, 'gcnArchName'):
            info['gcn_arch'] = props.gcnArchName
    print(json.dumps(info))
except ImportError:
    print(json.dumps({'error': 'torch not installed'}))
except Exception as e:
    print(json.dumps({'error': str(e)}))
"""
    try:
        result = subprocess.run(
            [python_exe, "-c", script],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout.strip())
    except Exception as e:
        return {'error': str(e)}
    return {'error': 'detection failed'}


def get_gpu_type(info: dict) -> str:
    """Determine GPU type from detection info."""
    if 'error' in info:
        return GPUType.UNKNOWN
    if info.get('hip_version'):
        return GPUType.AMD
    if info.get('cuda_version'):
        return GPUType.NVIDIA
    if info.get('cuda_available') and info.get('device_count', 0) > 0:
        name = info.get('device_name', '').lower()
        if 'amd' in name or 'radeon' in name:
            return GPUType.AMD
        if 'intel' in name:
            return GPUType.INTEL
        return GPUType.NVIDIA
    return GPUType.CPU


def get_torch_versions_for_gpu(gpu_type: str) -> list:
    """Get available PyTorch versions for the given GPU type."""
    versions = {
        GPUType.NVIDIA: [
            {"name": "Torch 2.9.1 (CUDA 13.0)", "cmd": "pip install torch==2.9.1 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130"},
            {"name": "Torch 2.9.1 (CUDA 12.8)", "cmd": "pip install torch==2.9.1 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128"},
            {"name": "Torch 2.7.0 (CUDA 12.8) + xFormers", "cmd": "pip install torch==2.7.0 torchvision torchaudio xformers --index-url https://download.pytorch.org/whl/cu128"},
            {"name": "Torch 2.6.0 (CUDA 12.6) + xFormers", "cmd": "pip install torch==2.6.0 torchvision torchaudio xformers --index-url https://download.pytorch.org/whl/cu126"},
            {"name": "Torch 2.5.1 (CUDA 12.4) + xFormers", "cmd": "pip install torch==2.5.1 torchvision torchaudio xformers --index-url https://download.pytorch.org/whl/cu124"},
        ],
        GPUType.AMD: [
            {"name": "Torch 2.13.0 (ROCm 10.0)", "cmd": "pip install torch==2.13.0+rocm10.0.0 torchvision==0.28.0+rocm10.0.0 torchaudio==2.11.0.2+rocm10.0.0 --index-url https://download.pytorch.org/whl/rocm10.0"},
            {"name": "Torch 2.7.0 (ROCm 7.0)", "cmd": "pip install torch==2.7.0+rocm7.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm7.0"},
            {"name": "Torch 2.6.0 (ROCm 6.3)", "cmd": "pip install torch==2.6.0+rocm6.3 torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.3"},
        ],
        GPUType.INTEL: [
            {"name": "Torch 2.7.0 (Intel XPU)", "cmd": "pip install torch==2.7.0a0+git881677d torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/xpu"},
            {"name": "Torch 2.6.0 (Intel XPU)", "cmd": "pip install torch==2.6.0+xpu torchvision torchaudio --index-url https://download.pytorch.org/whl/xpu"},
        ],
        GPUType.CPU: [
            {"name": "Torch 2.9.1 (CPU)", "cmd": "pip install torch==2.9.1 torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu"},
            {"name": "Torch 2.7.0 (CPU)", "cmd": "pip install torch==2.7.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu"},
        ],
    }
    return versions.get(gpu_type, [])
