"""Configuration manager for ClipBeam."""
import json
import os
import sys
import socket
from pathlib import Path
from typing import Dict, Any, List

DEFAULT_CONFIG: Dict[str, Any] = {
    "my_port": 58888,
    "peer_ip": "",
    "peer_port": 58888,
    "secret_key": "ClipBeamSecret2026",
    "hotkey_modifiers": ["ctrl", "alt"],
    "hotkey_key": "c",
    "auto_sync": False,
    "show_notifications": True,
    "play_sound": True,
    "start_with_windows": False,
    "max_history": 10
}

def get_base_dir() -> Path:
    """Return the directory of the running script or frozen executable."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

def get_resource_path(relative_path: str) -> Path:
    """Get absolute path to resource, works for dev and for PyInstaller onefile."""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / relative_path
    return get_base_dir() / relative_path

def get_config_path() -> Path:
    """Return path to config.json, preferring app directory with fallback to %APPDATA%."""
    base_dir = get_base_dir()
    local_path = base_dir / "clipbeam_config.json"
    
    # Check if local directory is writable
    try:
        if local_path.exists():
            return local_path
        # Try writing a tiny test file
        test_file = base_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
        return local_path
    except (PermissionError, OSError):
        appdata = Path(os.environ.get("APPDATA", str(Path.home()))) / "ClipBeam"
        appdata.mkdir(parents=True, exist_ok=True)
        return appdata / "clipbeam_config.json"

class ConfigManager:
    def __init__(self):
        self.config_path = get_config_path()
        self.config: Dict[str, Any] = dict(DEFAULT_CONFIG)
        self.load()

    def load(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.config.update(loaded)
            except Exception as e:
                print(f"[Config] Error loading config, using defaults: {e}")
        else:
            self.save()
        return self.config

    def save(self) -> bool:
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
            return True
        except Exception as e:
            print(f"[Config] Error saving config: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default if default is not None else DEFAULT_CONFIG.get(key))

    def set(self, key: str, value: Any):
        self.config[key] = value

    def update(self, new_settings: Dict[str, Any]):
        self.config.update(new_settings)
        self.save()

    @staticmethod
    def get_local_ips() -> List[str]:
        """Discover active local IPv4 addresses on this PC."""
        ips = set()
        # Method 1: Hostname lookup
        try:
            hostname = socket.gethostname()
            for ip in socket.gethostbyname_ex(hostname)[2]:
                if not ip.startswith("127.") and not ip.startswith("169.254."):
                    ips.add(ip)
        except Exception:
            pass

        # Method 2: Route lookup through UDP probe
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            candidate = s.getsockname()[0]
            if not candidate.startswith("127."):
                ips.add(candidate)
            s.close()
        except Exception:
            pass

        # Sort so typical LAN addresses (192.168.x.x, 10.x.x.x) show up logically
        def ip_sort_key(ip: str):
            if ip.startswith("192.168."):
                return (0, ip)
            if ip.startswith("10."):
                return (1, ip)
            if ip.startswith("172."):
                return (2, ip)
            return (3, ip)

        return sorted(list(ips), key=ip_sort_key)

    @staticmethod
    def update_windows_startup(enable: bool) -> bool:
        """Create or remove startup shortcut in Shell:Startup."""
        try:
            import win32com.client
            startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            if not startup_dir.exists():
                return False
            shortcut_path = startup_dir / "ClipBeam.lnk"

            if enable:
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(str(shortcut_path))
                if getattr(sys, 'frozen', False):
                    target = sys.executable
                else:
                    target = str(Path(sys.executable).parent / "pythonw.exe")
                    shortcut.Arguments = f'"{Path(__file__).resolve().parent / "main.py"}"'
                shortcut.TargetPath = target
                shortcut.WorkingDirectory = str(get_base_dir())
                shortcut.Description = "ClipBeam LAN Clipboard Sync"
                icon_path = get_base_dir() / "clipbeam.ico"
                if icon_path.exists():
                    shortcut.IconLocation = str(icon_path)
                shortcut.save()
            else:
                if shortcut_path.exists():
                    shortcut_path.unlink()
            return True
        except Exception as e:
            print(f"[Startup] Error updating startup shortcut: {e}")
            return False
