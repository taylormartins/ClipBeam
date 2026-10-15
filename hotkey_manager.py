"""Windows native global hotkey manager using Win32 RegisterHotKey."""
import ctypes
import threading
import time
from ctypes import wintypes
from typing import Callable, List, Optional

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

class HotkeyManager:
    def __init__(self, on_hotkey_pressed: Callable[[], None]):
        self.on_hotkey_pressed = on_hotkey_pressed
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._running = False
        self._hotkey_id = 1001

        self.modifiers = ["ctrl", "alt"]
        self.key = "c"

    def _parse_vk(self, key_str: str) -> int:
        key_upper = key_str.strip().upper()
        if len(key_upper) == 1:
            return ord(key_upper)
        if key_upper.startswith("F") and key_upper[1:].isdigit():
            f_num = int(key_upper[1:])
            if 1 <= f_num <= 24:
                return 0x6F + f_num
        special_keys = {
            "SPACE": 0x20,
            "TAB": 0x09,
            "INSERT": 0x2D,
            "DELETE": 0x2E,
            "HOME": 0x24,
            "END": 0x23,
            "PAGEUP": 0x21,
            "PAGEDOWN": 0x22
        }
        return special_keys.get(key_upper, ord('C'))

    def _parse_modifiers(self, mods: List[str]) -> int:
        flags = MOD_NOREPEAT
        for m in mods:
            m_lower = m.strip().lower()
            if m_lower in ("ctrl", "control"):
                flags |= MOD_CONTROL
            elif m_lower in ("alt",):
                flags |= MOD_ALT
            elif m_lower in ("shift",):
                flags |= MOD_SHIFT
            elif m_lower in ("win", "windows", "super"):
                flags |= MOD_WIN
        return flags

    def start(self, modifiers: List[str], key: str):
        self.stop()
        self.modifiers = modifiers
        self.key = key
        self._running = True

        ready_event = threading.Event()
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(ready_event,),
            daemon=True,
            name="HotkeyListenerThread"
        )
        self._thread.start()
        ready_event.wait(timeout=2.0)

    def stop(self):
        if not self._running:
            return
        self._running = False
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        self._thread_id = None

    def _run_loop(self, ready_event: threading.Event):
        self._thread_id = kernel32.GetCurrentThreadId()

        mod_flags = self._parse_modifiers(self.modifiers)
        vk = self._parse_vk(self.key)

        success = user32.RegisterHotKey(None, self._hotkey_id, mod_flags, vk)
        ready_event.set()

        if not success:
            print(f"[Hotkey] Failed to register global hotkey ({'+'.join(self.modifiers)}+{self.key})")
            return

        print(f"[Hotkey] Successfully registered global hotkey: {'+'.join(self.modifiers)}+{self.key.upper()}")

        msg = wintypes.MSG()
        try:
            while self._running:
                # Use PeekMessage or GetMessage
                ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if ret <= 0:
                    break
                if msg.message == WM_HOTKEY and msg.wParam == self._hotkey_id:
                    if self.on_hotkey_pressed:
                        # Dispatch callback in a separate thread so message loop isn't delayed
                        threading.Thread(target=self.on_hotkey_pressed, daemon=True).start()
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            user32.UnregisterHotKey(None, self._hotkey_id)
            print("[Hotkey] Unregistered global hotkey")
