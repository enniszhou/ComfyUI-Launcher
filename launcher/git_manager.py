"""Git version/branch management for ComfyUI."""
import os
from .utils import run_command


def find_git() -> str:
    """Find git executable."""
    import shutil
    git = shutil.which("git")
    return git or "git"


def get_current_branch(git_exe: str, cwd: str) -> str:
    rc, out, _ = run_command([git_exe, "branch", "--show-current"], cwd=cwd)
    return out.strip() if rc == 0 else ""


def get_current_commit(git_exe: str, cwd: str) -> str:
    rc, out, _ = run_command([git_exe, "log", "--oneline", "-1"], cwd=cwd)
    return out.strip() if rc == 0 else ""


def get_branches(git_exe: str, cwd: str) -> list:
    rc, out, _ = run_command([git_exe, "branch", "-a"], cwd=cwd)
    if rc != 0:
        return []
    branches = []
    for line in out.strip().splitlines():
        line = line.strip()
        if line.startswith("* "):
            line = line[2:]
        if "->" in line:
            continue
        line = line.replace("remotes/origin/", "")
        if line and line not in branches:
            branches.append(line)
    return branches


def get_tags(git_exe: str, cwd: str) -> list:
    rc, out, _ = run_command([git_exe, "tag", "-l", "--sort=-v:refname"], cwd=cwd)
    if rc != 0:
        return []
    return [t.strip() for t in out.strip().splitlines() if t.strip()]


def switch_branch(git_exe: str, cwd: str, branch: str) -> tuple:
    rc, out, err = run_command([git_exe, "checkout", branch], cwd=cwd)
    return rc == 0, out + err


def switch_tag(git_exe: str, cwd: str, tag: str) -> tuple:
    rc, out, err = run_command([git_exe, "checkout", tag], cwd=cwd)
    return rc == 0, out + err


def pull(git_exe: str, cwd: str) -> tuple:
    rc, out, err = run_command([git_exe, "pull"], cwd=cwd)
    return rc == 0, out + err


def fetch(git_exe: str, cwd: str) -> tuple:
    rc, out, err = run_command([git_exe, "fetch", "--all", "--tags"], cwd=cwd)
    return rc == 0, out + err


def get_log(git_exe: str, cwd: str, count: int = 20) -> list:
    rc, out, _ = run_command([git_exe, "log", f"-{count}", "--oneline"], cwd=cwd)
    if rc != 0:
        return []
    return [l.strip() for l in out.strip().splitlines() if l.strip()]
