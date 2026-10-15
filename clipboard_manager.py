"""Thread-safe and retry-resilient Windows clipboard manager."""
import time
import ctypes
from typing import Optional, Tuple
import win32clipboard as wcb
import win32con

user32 = ctypes.windll.user32

class ClipboardManager:
    @staticmethod
    def get_sequence_number() -> int:
        """Returns the Windows clipboard sequence number (increments every time clipboard updates)."""
        try:
            return user32.GetClipboardSequenceNumber()
        except Exception:
            return 0

    @classmethod
    def get_text(cls, max_retries: int = 5, retry_delay: float = 0.05) -> Tuple[bool, str, str]:
        """
        Safely retrieve UTF-8 / Unicode text from Windows clipboard with retries.
        Returns: (success, text, error_msg)
        """
        last_error = ""
        for attempt in range(max_retries):
            try:
                wcb.OpenClipboard()
                try:
                    if wcb.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                        data = wcb.GetClipboardData(win32con.CF_UNICODETEXT)
                        return True, data or "", ""
                    else:
                        return False, "", "Clipboard does not contain text."
                finally:
                    wcb.CloseClipboard()
            except Exception as e:
                last_error = str(e)
                time.sleep(retry_delay)
        return False, "", f"Unable to open clipboard: {last_error}"

    @classmethod
    def set_text(cls, text: str, max_retries: int = 5, retry_delay: float = 0.05) -> Tuple[bool, str]:
        """
        Safely write Unicode text to Windows clipboard with retries.
        Returns: (success, error_msg)
        """
        last_error = ""
        for attempt in range(max_retries):
            try:
                wcb.OpenClipboard()
                try:
                    wcb.EmptyClipboard()
                    wcb.SetClipboardData(win32con.CF_UNICODETEXT, text)
                    return True, ""
                finally:
                    wcb.CloseClipboard()
            except Exception as e:
                last_error = str(e)
                time.sleep(retry_delay)
        return False, f"Failed to set clipboard: {last_error}"

    @staticmethod
    def get_summary(text: str, max_preview_len: int = 40) -> str:
        """Generate human-readable summary of text snippet or log."""
        if not text:
            return "Empty clipboard"
        lines = text.count("\n") + 1
        size_bytes = len(text.encode("utf-8"))
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes / (1024 * 1024):.2f} MB"

        first_line = text.strip().split("\n")[0].strip()
        if len(first_line) > max_preview_len:
            preview = first_line[:max_preview_len] + "..."
        else:
            preview = first_line

        if lines > 1:
            return f"{lines} lines ({size_str}): {preview}"
        return f"{size_str}: {preview}"
