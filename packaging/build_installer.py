"""Build a single offline Windows installer directly from local app components."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release"
EXE = RELEASE / "LocalStudio-Setup.exe"
BUILD_EXE = RELEASE / "LocalStudio-Setup.next.exe"
BOOTSTRAP = RELEASE / "_bootstrap.exe"
PY_BASE = Path(sys.base_prefix)
PLAYWRIGHT = Path(os.environ["LOCALAPPDATA"]) / "ms-playwright"
CSC = Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe")
COMPRESSION = CSC.parent / "System.IO.Compression.dll"

ROOT_PRIVATE_DIRS = {
    "browser_data", "data", "processed_videos", "_cache_artifact",
    "__pycache__", "test", "tests", "_preview", "user_bgmusic",
    "user_intro_outro", "user_logos", "translation_memory",
}
PRIVATE_FILES = {
    "secret.key", "key_store.dat.lock", "data_khach.db",
    "metadata_index.db", "app_settings.json", "app_config.json",
    "theo_doi_config.json", "trang_config.json", "xu_ly_config.json",
    "_login_check.json", "_kiem_moi_truong.json", "_gpu_auto.json",
}
BUNDLED_BROWSER_MODULES = {
    "MediaCrawler/media_platform/bilibili/core.py",
    "MediaCrawler/media_platform/tieba/core.py",
    "MediaCrawler/media_platform/zhihu/core.py",
    "MediaCrawler/media_platform/kuaishou/core.py",
    "MediaCrawler/media_platform/weibo/core.py",
}


def excluded_app(directory: Path, name: str) -> bool:
    rel = directory.relative_to(ROOT / "src")
    if name in PRIVATE_FILES or name == "__pycache__" or name.endswith(".log"):
        return True
    return rel in (Path("."), Path("MediaCrawler")) and name in ROOT_PRIVATE_DIRS


def excluded_runtime(directory: Path, name: str) -> bool:
    if name == "__pycache__" or name.endswith(".pyc"):
        return True
    return directory.name == "site-packages" and name == "bin"


def add_tree(archive: zipfile.ZipFile, source: Path, target: str,
             excluded) -> int:
    count = 0
    for base, dirs, files in os.walk(source):
        directory = Path(base)
        dirs[:] = sorted(d for d in dirs if not excluded(directory, d))
        for name in sorted(files):
            if excluded(directory, name):
                continue
            path = directory / name
            relative = path.relative_to(source).as_posix()
            if target == "src" and relative in BUNDLED_BROWSER_MODULES:
                code = path.read_text(encoding="utf-8")
                if code.count('channel="chrome"') != 2:
                    raise RuntimeError(f"Unexpected Chrome launcher code: {path}")
                archive.writestr(f"{target}/{relative}",
                                 code.replace('channel="chrome"', 'channel=None'))
            else:
                archive.write(path, f"{target}/{relative}")
            count += 1
            if count % 3000 == 0:
                print(f"  {target}: {count} files", flush=True)
    return count


def add_file(archive: zipfile.ZipFile, source: Path, target: str) -> None:
    if not source.is_file():
        raise RuntimeError(f"Missing build input: {source}")
    archive.write(source, target)


def compile_bootstrap() -> None:
    result = subprocess.run([
        str(CSC), "/nologo", "/target:exe", "/platform:x64",
        f"/out:{BOOTSTRAP}", f"/reference:{COMPRESSION}",
        str(ROOT / "packaging" / "InstallerBootstrap.cs"),
    ], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)


def build() -> None:
    RELEASE.mkdir(exist_ok=True)
    compile_bootstrap()
    shutil.copy2(BOOTSTRAP, BUILD_EXE)
    count = 0
    try:
        with zipfile.ZipFile(BUILD_EXE, "a", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6, allowZip64=True) as archive:
            add_file(archive, ROOT / "local_server.py", "local_server.py")
            count += 1 + add_tree(archive, ROOT / "src", "src", excluded_app)

            for name in ("python.exe", "pythonw.exe", "python3.dll",
                         "python311.dll", "vcruntime140.dll",
                         "vcruntime140_1.dll", "LICENSE.txt"):
                add_file(archive, PY_BASE / name, f"runtime/{name}")
                count += 1
            for name in ("DLLs", "Lib", "tcl"):
                count += add_tree(archive, PY_BASE / name,
                                  f"runtime/{name}", excluded_runtime)

            for name in ("python.exe", "pythonw.exe"):
                add_file(archive, ROOT / ".venv" / "Scripts" / name,
                         f".venv/Scripts/{name}")
                count += 1
            count += add_tree(archive, ROOT / ".venv" / "Lib" / "site-packages",
                              ".venv/Lib/site-packages", excluded_runtime)
            archive.writestr(".venv/pyvenv.cfg",
                             "home = INSTALLER_REWRITES_THIS\n"
                             "include-system-site-packages = false\n"
                             "version_info = 3.11\n")
            count += 1

            for name in ("chromium-1243", "chromium_headless_shell-1243",
                         "ffmpeg-1011"):
                count += add_tree(archive, PLAYWRIGHT / name,
                                  f"browser/{name}", excluded_runtime)

            ffmpeg = Path(os.environ["APPDATA"]) / "SnapAny" / "tools" / "ffmpeg" / "8.0" / "ffmpeg.exe"
            ffprobe = Path(os.environ["APPDATA"]) / "SnapAny" / "tools" / "ffprobe" / "8.0" / "ffprobe.exe"
            for binary in (ffmpeg, ffprobe):
                add_file(archive, binary, f"bin/{binary.name}")
                count += 1

            archive.writestr("RUN-LOCAL-STUDIO.cmd",
                '@echo off\r\n'
                'cd /d "%~dp0"\r\n'
                'set "PATH=%~dp0.venv\\Scripts;%~dp0bin;%PATH%"\r\n'
                'set "PLAYWRIGHT_BROWSERS_PATH=%~dp0browser"\r\n'
                'start "" "%~dp0.venv\\Scripts\\pythonw.exe" "%~dp0local_server.py"\r\n'
                'timeout /t 3 /nobreak >nul\r\n'
                'start "" "http://127.0.0.1:8770/"\r\n')
            count += 1
    finally:
        if BOOTSTRAP.is_file() and BOOTSTRAP.resolve().parent == RELEASE.resolve():
            BOOTSTRAP.unlink()

    result = subprocess.run([str(BUILD_EXE), "--selftest"],
                            capture_output=True, text=True, timeout=120)
    if result.returncode or "ZIP_OK" not in result.stdout:
        raise RuntimeError(f"Installer self-test failed: {result.stdout} {result.stderr}")
    with zipfile.ZipFile(BUILD_EXE, "r") as archive:
        names = set(archive.namelist())
        essential = {"local_server.py", "src/web_app.pyc", "src/web/index.html",
                     ".venv/Scripts/python.exe", "bin/ffmpeg.exe",
                     "RUN-LOCAL-STUDIO.cmd"}
        missing = essential - names
        if missing:
            raise RuntimeError(f"Installer missing: {sorted(missing)}")
        for name in names:
            if name.startswith("src/MediaCrawler/browser_data/") or name.startswith("src/MediaCrawler/data/"):
                raise RuntimeError(f"Private data included: {name}")
            if name in {"src/secret.key", "src/data_khach.db", "config_keys.json"}:
                raise RuntimeError(f"Private file included: {name}")
        for module in BUNDLED_BROWSER_MODULES:
            code = archive.read(f"src/{module}").decode("utf-8")
            if 'channel="chrome"' in code or code.count("channel=None") != 2:
                raise RuntimeError(f"Bundled browser fallback missing: {module}")
    os.replace(BUILD_EXE, EXE)
    print(f"EXE: {EXE}", flush=True)
    print(f"Size: {EXE.stat().st_size / 2**20:.1f} MiB, files: {count}", flush=True)
    print(result.stdout.strip(), flush=True)


if __name__ == "__main__":
    build()
