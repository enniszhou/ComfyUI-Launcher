"""Mirror configuration for pip, git, and HuggingFace."""
import os
import subprocess

PIP_MIRRORS = {
    "official": {
        "name": "PyPI Official",
        "url": "https://pypi.org/simple",
        "trusted": "",
    },
    "tsinghua": {
        "name": "Tsinghua (China)",
        "url": "https://pypi.tuna.tsinghua.edu.cn/simple",
        "trusted": "pypi.tuna.tsinghua.edu.cn",
    },
    "aliyun": {
        "name": "Aliyun (China)",
        "url": "https://mirrors.aliyun.com/pypi/simple",
        "trusted": "mirrors.aliyun.com",
    },
    "douban": {
        "name": "Douban (China)",
        "url": "https://pypi.doubanio.com/simple",
        "trusted": "pypi.doubanio.com",
    },
    "ustc": {
        "name": "USTC (China)",
        "url": "https://pypi.mirrors.ustc.edu.cn/simple",
        "trusted": "pypi.mirrors.ustc.edu.cn",
    },
    "huawei": {
        "name": "Huawei (China)",
        "url": "https://repo.huaweicloud.com/repository/pypi/simple",
        "trusted": "repo.huaweicloud.com",
    },
}

HF_MIRRORS = {
    "official": {
        "name": "HuggingFace Official",
        "url": "https://huggingface.co",
    },
    "hf-mirror": {
        "name": "HF Mirror (China)",
        "url": "https://hf-mirror.com",
    },
}

GIT_MIRRORS = {
    "official": {
        "name": "GitHub Official",
        "host": "github.com",
    },
    "ghproxy": {
        "name": "ghproxy (China)",
        "host": "ghproxy.com",
    },
}


def get_pip_mirror_config(mirror_key: str) -> dict:
    return PIP_MIRRORS.get(mirror_key, PIP_MIRRORS["official"])


def set_pip_mirror(python_exe: str, mirror_key: str) -> bool:
    mirror = get_pip_mirror_config(mirror_key)
    cmd = [python_exe, "-m", "pip", "config", "set", "global.index-url", mirror["url"]]
    try:
        subprocess.run(cmd, capture_output=True, timeout=10)
        if mirror["trusted"]:
            cmd2 = [python_exe, "-m", "pip", "config", "set", "global.trusted-host", mirror["trusted"]]
            subprocess.run(cmd2, capture_output=True, timeout=10)
        return True
    except Exception:
        return False


def get_current_pip_mirror(python_exe: str) -> str:
    try:
        result = subprocess.run(
            [python_exe, "-m", "pip", "config", "get", "global.index-url"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def set_hf_mirror(env: dict, mirror_key: str) -> dict:
    mirror = HF_MIRRORS.get(mirror_key, HF_MIRRORS["official"])
    if mirror_key == "official":
        env.pop("HF_ENDPOINT", None)
    else:
        env["HF_ENDPOINT"] = mirror["url"]
    return env


def set_git_proxy(git_exe: str, proxy_url: str = "") -> bool:
    try:
        if proxy_url:
            subprocess.run([git_exe, "config", "--global", "http.proxy", proxy_url],
                           capture_output=True, timeout=10)
            subprocess.run([git_exe, "config", "--global", "https.proxy", proxy_url],
                           capture_output=True, timeout=10)
        else:
            subprocess.run([git_exe, "config", "--global", "--unset", "http.proxy"],
                           capture_output=True, timeout=10)
            subprocess.run([git_exe, "config", "--global", "--unset", "https.proxy"],
                           capture_output=True, timeout=10)
        return True
    except Exception:
        return False
