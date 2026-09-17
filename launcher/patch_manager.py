"""Patch/hotfix management for ComfyUI."""
import os
import json
import shutil
from .utils import load_json_file, save_json_file


PATCHES_DIR_NAME = ".launcher_patches"
BACKUP_DIR_NAME = ".launcher_patches_backup"

BUILTIN_PATCHES = [
    {
        "id": "ipex_mem_alloc_slicing",
        "name": "IPEX Memory Alloc Slicing Fix",
        "description": "Fix memory allocation slicing for Intel IPEX GPUs",
        "files": ["comfy/model_management.py"],
        "default_disabled": True,
    },
    {
        "id": "ipex_antialias_interpolate",
        "name": "IPEX Antialias Interpolate Fix",
        "description": "Fix antialias interpolation for Intel IPEX",
        "files": ["comfy/model_management.py"],
        "default_disabled": True,
    },
    {
        "id": "torch_zluda_timer",
        "name": "Torch ZLUDA Timer Fix",
        "description": "Fix timer issues with ZLUDA backend",
        "files": ["comfy/model_management.py"],
        "default_disabled": True,
    },
    {
        "id": "einx_register",
        "name": "EINX Register Fix",
        "description": "Fix einx registration issues",
        "files": [],
        "default_disabled": True,
    },
    {
        "id": "rocm_attention_opt",
        "name": "ROCm Attention Optimization",
        "description": "Enable optimized attention for AMD ROCm GPUs",
        "files": ["comfy/model_management.py"],
        "default_disabled": False,
    },
    {
        "id": "rocm_flash_attn",
        "name": "ROCm Flash Attention",
        "description": "Enable flash attention support for ROCm",
        "files": ["comfy/model_management.py"],
        "default_disabled": False,
    },
]


class PatchManager:
    def __init__(self, comfyui_dir: str):
        self.comfyui_dir = comfyui_dir
        self.patches_dir = os.path.join(comfyui_dir, PATCHES_DIR_NAME)
        self.backup_dir = os.path.join(comfyui_dir, BACKUP_DIR_NAME)
        self.state_file = os.path.join(self.patches_dir, "state.json")
        os.makedirs(self.patches_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)

    def get_state(self) -> dict:
        return load_json_file(self.state_file)

    def save_state(self, state: dict):
        save_json_file(self.state_file, state)

    def list_patches(self) -> list:
        state = self.get_state()
        result = []
        for p in BUILTIN_PATCHES:
            info = dict(p)
            info["applied"] = state.get(p["id"], {}).get("applied", False)
            info["enabled"] = not state.get(p["id"], {}).get("disabled", p.get("default_disabled", False))
            result.append(info)
        return result

    def apply_patch(self, patch_id: str) -> tuple:
        patch = None
        for p in BUILTIN_PATCHES:
            if p["id"] == patch_id:
                patch = p
                break
        if not patch:
            return False, f"Patch '{patch_id}' not found"

        state = self.get_state()
        patch_state = state.get(patch_id, {})

        if patch_state.get("applied"):
            return False, "Patch already applied"

        for rel_path in patch["files"]:
            src = os.path.join(self.comfyui_dir, rel_path)
            if not os.path.isfile(src):
                continue
            backup = os.path.join(self.backup_dir, rel_path.replace("/", "_") + ".bak")
            if not os.path.isfile(backup):
                os.makedirs(os.path.dirname(backup), exist_ok=True)
                shutil.copy2(src, backup)

        patch_state["applied"] = True
        state[patch_id] = patch_state
        self.save_state(state)
        return True, f"Applied patch '{patch_id}'"

    def revert_patch(self, patch_id: str) -> tuple:
        patch = None
        for p in BUILTIN_PATCHES:
            if p["id"] == patch_id:
                patch = p
                break
        if not patch:
            return False, f"Patch '{patch_id}' not found"

        state = self.get_state()
        patch_state = state.get(patch_id, {})

        if not patch_state.get("applied"):
            return False, "Patch not applied"

        for rel_path in patch["files"]:
            backup = os.path.join(self.backup_dir, rel_path.replace("/", "_") + ".bak")
            target = os.path.join(self.comfyui_dir, rel_path)
            if os.path.isfile(backup):
                shutil.copy2(backup, target)

        patch_state["applied"] = False
        state[patch_id] = patch_state
        self.save_state(state)
        return True, f"Reverted patch '{patch_id}'"

    def toggle_enabled(self, patch_id: str) -> tuple:
        state = self.get_state()
        patch_state = state.get(patch_id, {})
        currently_disabled = patch_state.get("disabled", False)
        patch_state["disabled"] = not currently_disabled
        state[patch_id] = patch_state
        self.save_state(state)

        if patch_state.get("applied") and patch_state["disabled"]:
            return self.revert_patch(patch_id)
        elif not patch_state.get("applied") and not patch_state["disabled"]:
            return self.apply_patch(patch_id)

        return True, f"{'Disabled' if patch_state['disabled'] else 'Enabled'} '{patch_id}'"
