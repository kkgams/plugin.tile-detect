"""Remove disposable build output, tools and installed Units after safety checks."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PATHS = ("build.nosync", "tools", "gams_modules")

# Validate every target before deleting anything. Never traverse symlinks.
for name in PATHS:
    path = ROOT / name
    for part in (path, *path.parents):
        if part == ROOT:
            break
        if part.is_symlink():
            raise SystemExit(f"Refusing symlink in clean path: {part.relative_to(ROOT)}")
    if path.is_dir():
        for child in path.rglob("*"):
            if child.is_symlink():
                raise SystemExit(f"Refusing symlink in clean path: {child.relative_to(ROOT)}")
    tracked = subprocess.check_output(
        ["git", "ls-files", "--", name], cwd=ROOT, text=True
    )
    if tracked:
        raise SystemExit(f"Refusing to remove tracked output files:\n{tracked}")

for name in PATHS:
    path = ROOT / name
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()
