"""Auto-updater module for ClipBeam to update from GitHub Releases."""
import os
import sys
import json
import time
import shutil
import tempfile
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Tuple, Optional, Callable

GITHUB_REPO = "taylormartins/ClipBeam"
CURRENT_VERSION = "v1.0.2"

def parse_version(tag: str) -> Tuple[int, ...]:
    clean = tag.strip().lstrip('vV')
    parts = []
    for p in clean.split('.'):
        if p.isdigit():
            parts.append(int(p))
    return tuple(parts)

class Updater:
    @staticmethod
    def check_for_updates(current_ver: str = CURRENT_VERSION, repo: str = GITHUB_REPO) -> Tuple[bool, str, str, str]:
        """
        Check GitHub releases for a newer version.
        Returns: (has_update: bool, latest_tag: str, download_url: str, release_notes: str)
        """
        api_url = f"https://api.github.com/repos/{repo}/releases/latest"
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "ClipBeam-AutoUpdater/1.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status != 200:
                    return False, "", "", f"GitHub API error: {response.status}"
                data = json.loads(response.read().decode("utf-8"))
                
                latest_tag = data.get("tag_name", "")
                notes = data.get("body", "")

                download_url = ""
                for asset in data.get("assets", []):
                    if asset.get("name") == "ClipBeam.exe":
                        download_url = asset.get("browser_download_url", "")
                        break

                if not download_url:
                    return False, latest_tag, "", "No ClipBeam.exe found in latest release."

                curr_tuple = parse_version(current_ver)
                latest_tuple = parse_version(latest_tag)

                if latest_tuple > curr_tuple:
                    return True, latest_tag, download_url, notes
                return False, latest_tag, download_url, "Already up to date."
        except Exception as e:
            return False, "", "", f"Failed to check updates: {str(e)}"

    @staticmethod
    def apply_update(download_url: str, on_status: Optional[Callable[[str], None]] = None) -> Tuple[bool, str]:
        """
        Download new ClipBeam.exe and restart with the updated executable.
        """
        try:
            if not getattr(sys, 'frozen', False):
                return False, "Self-update is only supported when running as compiled ClipBeam.exe (use git pull in dev)."

            current_exe = Path(sys.executable).resolve()
            temp_dir = Path(tempfile.gettempdir())
            temp_exe = temp_dir / f"ClipBeam_update_{int(time.time())}.exe"

            if on_status:
                on_status("Downloading latest ClipBeam.exe...")

            req = urllib.request.Request(download_url, headers={"User-Agent": "ClipBeam-AutoUpdater/1.0"})
            with urllib.request.urlopen(req, timeout=30) as response, open(temp_exe, "wb") as out_file:
                shutil.copyfileobj(response, out_file)

            if not temp_exe.exists() or temp_exe.stat().st_size < 1024 * 1024:
                return False, "Downloaded file is invalid or incomplete."

            if on_status:
                on_status("Applying update and restarting...")

            # Write temporary batch script to swap executables and relaunch
            bat_path = temp_dir / f"clipbeam_updater_{int(time.time())}.bat"
            bat_content = f"""@echo off
timeout /t 1 /nobreak >nul
:retry
taskkill /f /im ClipBeam.exe >nul 2>&1
timeout /t 1 /nobreak >nul
move /y "{temp_exe}" "{current_exe}" >nul 2>&1
if exist "{temp_exe}" (
    timeout /t 1 /nobreak >nul
    goto retry
)
start "" "{current_exe}"
del "%~f0"
"""
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(bat_content)

            # Spawn batch updater detached with no console window
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen(["cmd.exe", "/c", str(bat_path)], creationflags=CREATE_NO_WINDOW, close_fds=True)

            # Exit current application so the file is freed for moving
            sys.exit(0)
            return True, "Update initiated"
        except Exception as e:
            return False, f"Update failed: {str(e)}"
