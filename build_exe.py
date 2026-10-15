"""Build script to compile ClipBeam into a standalone single-file Windows executable."""
import os
import sys
import shutil
import subprocess
from pathlib import Path

def build():
    base_dir = Path(__file__).resolve().parent
    icon_path = base_dir / "clipbeam.ico"
    png_path = base_dir / "clipbeam.png"

    if not icon_path.exists() or not png_path.exists():
        print("[Build] Generating icons first...")
        subprocess.run([sys.executable, str(base_dir / "icon_gen.py")], check=True)

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",              # No terminal console window
        "--name", "ClipBeam",
        f"--icon={icon_path}",
        f"--add-data={icon_path};.",
        f"--add-data={png_path};.",
        "--hidden-import=win32clipboard",
        "--hidden-import=win32con",
        "--hidden-import=win32api",
        "--hidden-import=win32gui",
        "--hidden-import=win32com",
        "--hidden-import=win32com.client",
        "--hidden-import=pystray._win32",
        "--hidden-import=cryptography",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=tkinter",
        str(base_dir / "main.py")
    ]

    print("[Build] Executing command:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=str(base_dir))
    if res.returncode == 0:
        exe_path = base_dir / "dist" / "ClipBeam.exe"
        print(f"\n[Build SUCCESS] Executable created at: {exe_path}")
        print(f"[Build SUCCESS] File size: {exe_path.stat().st_size / (1024*1024):.2f} MB")
    else:
        print("\n[Build FAILED] PyInstaller returned error code:", res.returncode)

if __name__ == "__main__":
    build()
