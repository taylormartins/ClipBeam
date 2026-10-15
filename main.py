"""ClipBeam - Encrypted Peer-to-Peer LAN Clipboard Beamer for Windows.
Main application entry point.
"""
import os
import sys
import time
import winsound
import threading
from pathlib import Path
from typing import Optional, List
from PIL import Image

import pystray
from pystray import MenuItem as item, Menu

from config_manager import ConfigManager, get_base_dir, get_resource_path
from crypto_manager import CryptoManager
from clipboard_manager import ClipboardManager
from history_manager import HistoryManager, HistoryItem
from network_server import ClipBeamServer
from network_client import NetworkClient
from hotkey_manager import HotkeyManager
from settings_window import SettingsWindow
from updater import Updater, CURRENT_VERSION

APP_VERSION = CURRENT_VERSION

class ClipBeamApp:
    def __init__(self):
        self.cfg_mgr = ConfigManager()
        self.history = HistoryManager(max_items=self.cfg_mgr.get("max_history", 10))
        
        self.icon: Optional[pystray.Icon] = None
        self.server: Optional[ClipBeamServer] = None
        self.hotkey_mgr: Optional[HotkeyManager] = None
        self.settings_win: Optional[SettingsWindow] = None

        self._running = True
        self._last_seq = 0
        self._last_sent_text = ""
        self._skip_next_sync = False
        self._sync_thread: Optional[threading.Thread] = None

    def start(self):
        # 1. Start Server
        self._start_server()

        # 2. Start Global Hotkey (grab_active=True automatically captures highlighted text!)
        self.hotkey_mgr = HotkeyManager(on_hotkey_pressed=lambda: self.beam_clipboard_now(grab_active=True))
        self._apply_hotkey()

        # 3. Start Auto-Sync Poller
        self._last_seq = ClipboardManager.get_sequence_number()
        self._sync_thread = threading.Thread(target=self._auto_sync_loop, daemon=True, name="AutoSyncWatcher")
        self._sync_thread.start()

        # 4. Initialize Settings Window Manager
        self.settings_win = SettingsWindow(self.cfg_mgr, on_save_callback=self._on_settings_saved, on_check_updates=self.check_for_updates_ui)

        # 5. Start System Tray Icon
        self._run_tray_icon()

    def _start_server(self):
        if self.server:
            self.server.stop()
        port = int(self.cfg_mgr.get("my_port", 58888))
        self.server = ClipBeamServer(
            port=port,
            get_secret_key=lambda: self.cfg_mgr.get("secret_key", "ClipBeamSecret2026"),
            on_received=self._on_clipboard_received
        )
        ok, msg = self.server.start()
        print(f"[Server] {msg}")

    def _apply_hotkey(self):
        mods = self.cfg_mgr.get("hotkey_modifiers", ["ctrl", "shift"])
        key = self.cfg_mgr.get("hotkey_key", "c")
        if self.hotkey_mgr:
            self.hotkey_mgr.start(mods, key)

    def _on_settings_saved(self, new_settings: dict):
        # Restart server if port changed
        self._start_server()
        # Re-register hotkey
        self._apply_hotkey()
        # Update tray menu
        self._update_tray_menu()
        self.show_notification("ClipBeam", "Settings updated successfully!")

    def _load_icon_image(self) -> Image.Image:
        icon_path = get_resource_path("clipbeam.png")
        if icon_path.exists():
            try:
                return Image.open(icon_path)
            except Exception:
                pass
        ico_path = get_resource_path("clipbeam.ico")
        if ico_path.exists():
            try:
                return Image.open(ico_path)
            except Exception:
                pass

        # Fallback dynamic icon
        img = Image.new('RGBA', (64, 64), color=(15, 23, 42, 255))
        return img

    def _run_tray_icon(self):
        image = self._load_icon_image()
        self.icon = pystray.Icon(
            "ClipBeam",
            image,
            f"ClipBeam {APP_VERSION} - LAN Clipboard Sync",
            menu=self._build_menu()
        )
        # Notify user that ClipBeam is running in tray
        hk_display = "+".join(m.upper() for m in self.cfg_mgr.get("hotkey_modifiers", ["ctrl", "shift"])) + f"+{self.cfg_mgr.get('hotkey_key', 'c').upper()}"
        print(f"[ClipBeam] Running in tray. Shortcut: {hk_display}")

        # Show initial notification on launch
        threading.Thread(target=self._initial_notify, daemon=True).start()

        # Run tray loop (blocking call on main thread)
        self.icon.run()

    def _initial_notify(self):
        time.sleep(1.0)
        hk_display = "+".join(m.upper() for m in self.cfg_mgr.get("hotkey_modifiers", ["ctrl", "shift"])) + f"+{self.cfg_mgr.get('hotkey_key', 'c').upper()}"
        peer_ip = self.cfg_mgr.get("peer_ip", "")
        peer_str = f"Peer: {peer_ip}" if peer_ip else "Configure peer IP in Settings"
        self.show_notification(f"⚡ ClipBeam {APP_VERSION} Ready", f"Shortcut: {hk_display}\n{peer_str}")

    def _build_menu(self) -> Menu:
        hk_display = "+".join(m.upper() for m in self.cfg_mgr.get("hotkey_modifiers", ["ctrl", "shift"])) + f"+{self.cfg_mgr.get('hotkey_key', 'c').upper()}"
        
        # Recent clips submenu
        recent_items = []
        history_list = self.history.get_all()
        if not history_list:
            recent_items.append(item("(No recent clips)", lambda: None, enabled=False))
        else:
            for idx, h in enumerate(history_list):
                prefix = "↓ " if h.direction == "received" else "↑ "
                label = f"{prefix}{h.summary}"
                if len(label) > 45:
                    label = label[:42] + "..."
                # Closure to capture h.text
                def make_copy_func(text_to_copy):
                    return lambda: self._recopy_clip(text_to_copy)
                recent_items.append(item(label, make_copy_func(h.text)))

        auto_sync_active = self.cfg_mgr.get("auto_sync", False)

        menu_items = [
            item(f"⚡ Beam Clipboard Now ({hk_display})", lambda: self.beam_clipboard_now(grab_active=False), default=True),
            item("📋 Recent Clips", Menu(*recent_items)),
            Menu.SEPARATOR,
            item("🔄 Auto-Sync Clipboard", self._toggle_auto_sync, checked=lambda item: self.cfg_mgr.get("auto_sync", False)),
            item("⚙️ Settings...", lambda: self._open_settings()),
            item("📡 Ping Peer", lambda: self._ping_peer_manual()),
            item("⬇️ Check for Updates...", lambda: self.check_for_updates_ui()),
            Menu.SEPARATOR,
            item("❌ Exit ClipBeam", lambda: self.exit_app())
        ]
        return Menu(*menu_items)

    def _update_tray_menu(self):
        if self.icon:
            try:
                self.icon.menu = self._build_menu()
                self.icon.update_menu()
            except Exception:
                pass

    def _recopy_clip(self, text: str):
        self._skip_next_sync = True
        ok, err = ClipboardManager.set_text(text)
        if ok:
            summary = ClipboardManager.get_summary(text)
            self.show_notification("📋 Restored to Clipboard", summary)
        else:
            self.show_notification("❌ Copy Error", err)

    def _toggle_auto_sync(self):
        curr = self.cfg_mgr.get("auto_sync", False)
        new_val = not curr
        self.cfg_mgr.set("auto_sync", new_val)
        self.cfg_mgr.save()
        status_str = "Enabled" if new_val else "Disabled"
        self.show_notification("🔄 Auto-Sync", f"Auto-sync on clipboard copy is now {status_str}.")
        self._update_tray_menu()

    def _open_settings(self):
        if self.settings_win:
            threading.Thread(target=self.settings_win.show, daemon=True).start()

    def _ping_peer_manual(self):
        def _worker():
            peer_ip = self.cfg_mgr.get("peer_ip", "")
            port = int(self.cfg_mgr.get("peer_port", 58888))
            ok, msg, _ = NetworkClient.ping_peer(peer_ip, port)
            title = "📡 Peer Online" if ok else "⚠️ Peer Unreachable"
            self.show_notification(title, msg)
        threading.Thread(target=_worker, daemon=True).start()

    def beam_clipboard_now(self, grab_active: bool = False):
        """Action to send the current Windows clipboard content to peer."""
        def _worker():
            peer_ip = self.cfg_mgr.get("peer_ip", "").strip()
            if not peer_ip:
                self.show_notification("⚠️ Setup Required", "Please set the other computer's IP in Settings first.")
                self._open_settings()
                return

            if grab_active:
                # Active selection grabbing: captures currently highlighted text directly!
                ok, text, err = ClipboardManager.grab_active_selection()
            else:
                ok, text, err = ClipboardManager.get_text()

            if not ok or not text.strip():
                self.show_notification("⚠️ Clipboard Notice", "Clipboard has no text to beam.")
                return

            port = int(self.cfg_mgr.get("peer_port", 58888))
            secret = self.cfg_mgr.get("secret_key", "ClipBeamSecret2026")
            summary = ClipboardManager.get_summary(text)

            success, msg = NetworkClient.send_clipboard(peer_ip, port, secret, text)
            if success:
                self._last_sent_text = text
                self.history.add("sent", text, summary, peer_ip)
                self._update_tray_menu()
                if self.cfg_mgr.get("show_notifications", True):
                    self.show_notification("⚡ Clipboard Beamed!", f"Sent to {peer_ip}\n{summary}")
            else:
                self.show_notification("❌ Beam Failed", msg)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_clipboard_received(self, text: str, sender: str, summary: str):
        """Called when server receives decrypted clipboard payload from peer."""
        # Prevent auto-sync from looping this received text back out
        self._skip_next_sync = True
        self._last_sent_text = text

        ok, err = ClipboardManager.set_text(text)
        if ok:
            self.history.add("received", text, summary, sender)
            self._update_tray_menu()

            if self.cfg_mgr.get("play_sound", True):
                try:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass

            if self.cfg_mgr.get("show_notifications", True):
                self.show_notification("📋 Clipboard Received!", f"From {sender}\n{summary}")
        else:
            self.show_notification("❌ Clipboard Error", f"Received data but failed to write to clipboard: {err}")

    def _auto_sync_loop(self):
        """Watches clipboard changes and automatically beams if auto_sync is enabled."""
        while self._running:
            time.sleep(0.4)
            if not self.cfg_mgr.get("auto_sync", False):
                continue

            curr_seq = ClipboardManager.get_sequence_number()
            if curr_seq != self._last_seq:
                self._last_seq = curr_seq

                if self._skip_next_sync:
                    self._skip_next_sync = False
                    continue

                # Check text content
                ok, text, _ = ClipboardManager.get_text()
                if ok and text and text != self._last_sent_text:
                    self._last_sent_text = text
                    self.beam_clipboard_now(grab_active=False)

    def check_for_updates_ui(self):
        """Check for updates from GitHub releases and prompt user."""
        def _worker():
            self.show_notification("🔍 Updates", "Checking GitHub for updates...")
            has_update, latest_tag, download_url, notes = Updater.check_for_updates(APP_VERSION)
            if not has_update:
                if latest_tag:
                    self.show_notification("✓ Up to Date", f"ClipBeam {APP_VERSION} is the latest version.")
                else:
                    self.show_notification("⚠️ Update Check", notes)
                return

            # An update is available! Show confirmation dialog via Tkinter
            def _prompt():
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                answer = messagebox.askyesno(
                    "ClipBeam Update Available",
                    f"A new version of ClipBeam is available: {latest_tag} (Current: {APP_VERSION})\n\n"
                    f"Would you like to download and install this update now?",
                    parent=root
                )
                root.destroy()
                if answer:
                    self.show_notification("⬇️ Updating", f"Downloading {latest_tag}...")
                    def on_status(msg):
                        self.show_notification("⬇️ Updating", msg)
                    ok, err = Updater.apply_update(download_url, on_status=on_status)
                    if not ok:
                        self.show_notification("❌ Update Failed", err)

            threading.Thread(target=_prompt, daemon=True).start()

        threading.Thread(target=_worker, daemon=True).start()

    def show_notification(self, title: str, message: str):
        """Show native Windows notification balloon/toast via tray icon."""
        if self.icon and self.cfg_mgr.get("show_notifications", True):
            try:
                self.icon.notify(message, title)
            except Exception as e:
                print(f"[Notification] {title}: {message} ({e})")

    def exit_app(self):
        """Clean shutdown."""
        self._running = False
        if self.hotkey_mgr:
            self.hotkey_mgr.stop()
        if self.server:
            self.server.stop()
        if self.settings_win:
            self.settings_win.close()
        if self.icon:
            self.icon.stop()
        sys.exit(0)

def main():
    try:
        app = ClipBeamApp()
        app.start()
    except Exception as e:
        import traceback
        log_file = get_base_dir() / "clipbeam_crash.log"
        with open(log_file, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)

if __name__ == "__main__":
    main()
