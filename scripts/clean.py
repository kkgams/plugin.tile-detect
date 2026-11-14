"""Remove generated output and identified Host downloads; preserve supplied Units."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
from urllib.parse import urldefrag, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PATHS = ["build.nosync"]
# Existing apps may be supplied by the user, not downloaded by this Makefile.
app = ROOT / "tools/gams.app"
notices = ROOT / "tools/gams-release-notices"
if app.exists() or app.is_symlink() or notices.exists() or notices.is_symlink():
    tools = ROOT / "tools"
    marker = notices / ".gams-managed"
    if tools.is_symlink() or app.is_symlink() or notices.is_symlink() or marker.is_symlink():
        raise SystemExit("Refusing symlink in Host clean paths")
    if not marker.is_file() or marker.read_text() != "plugin.tile-detect Makefile Host download\n":
        raise SystemExit("Refusing unidentified Host tools; preserve or move supplied tools aside")
    PATHS.extend(["tools/gams.app", "tools/gams-release-notices"])
modules = ROOT / "gams_modules"
if modules.is_symlink():
    raise SystemExit("Refusing symlink in clean path: gams_modules")

# Current Host cache keys exclude ZIP entry selectors. Only remove configured
# downloads with matching completion markers; unrelated/legacy caches stay put.
config = json.loads((ROOT / "gams.json").read_text())
ui = config["ui"]
sources = [*config["plugins"], ui["theme"]["url"]]
for group in (ui["views"], ui["services"]):
    sources.extend(entry["url"] for entry in group.values())
for source in sorted(set(sources)):
    url, _ = urldefrag(source)
    if urlsplit(url).scheme != "https":
        continue
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    path = modules / key
    if path.is_symlink():
        raise SystemExit(f"Refusing symlink in clean path: gams_modules/{key}")
    if not path.exists():
        continue
    marker = path / ".gams-resource.json"
    expected = {"version": 1, "url": url, "archive": urlsplit(url).path.lower().endswith(".zip")}
    if not marker.is_file() or marker.is_symlink() or json.loads(marker.read_text()) != expected:
        raise SystemExit(f"Refusing unidentified Unit cache: gams_modules/{key}")
    if not (path / "content").is_dir():
        raise SystemExit(f"Refusing incomplete Unit cache: gams_modules/{key}")
    PATHS.append(f"gams_modules/{key}")

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
if modules.is_dir() and not any(modules.iterdir()):
    modules.rmdir()
