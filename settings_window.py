"""Modern Settings UI for ClipBeam built with Tkinter."""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Callable, Dict, Any, List, Optional
from config_manager import ConfigManager
from network_client import NetworkClient

class SettingsWindow:
    def __init__(self, config_manager: ConfigManager, on_save_callback: Callable[[Dict[str, Any]], None], on_check_updates: Optional[Callable[[], None]] = None):
        self.cfg_mgr = config_manager
        self.on_save_callback = on_save_callback
        self.on_check_updates = on_check_updates
        self.root: Optional[tk.Tk] = None
        self._is_open = False

    def show(self):
        if self._is_open and self.root:
            try:
                self.root.lift()
                self.root.focus_force()
                return
            except Exception:
                self._is_open = False

        # Run UI in main or current thread
        self._create_window()

    def _create_window(self):
        self._is_open = True
        self.root = tk.Tk()
        self.root.title("ClipBeam - Configuration & Settings")
        self.root.geometry("540x660")
        self.root.resizable(False, False)

        # Apply modern dark/slate theme
        bg_main = "#0f172a"        # Slate 900
        bg_card = "#1e293b"        # Slate 800
        fg_white = "#f8fafc"       # Slate 50
        fg_muted = "#94a3b8"       # Slate 400
        accent_blue = "#0284c7"    # Sky 600
        accent_hover = "#0369a1"   # Sky 700
        border_color = "#334155"   # Slate 700

        self.root.configure(bg=bg_main)

        # Try setting taskbar icon if available
        try:
            from config_manager import get_resource_path
            icon_p = get_resource_path("clipbeam.ico")
            if icon_p.exists():
                self.root.iconbitmap(str(icon_p))
        except Exception:
            pass

        # Center on screen
        self.root.update_idletasks()
        w = 540
        h = 660
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        # Header Frame
        header = tk.Frame(self.root, bg=bg_card, height=65, padx=20, pady=12)
        header.pack(fill="x")

        title_lbl = tk.Label(header, text="⚡ ClipBeam Settings", font=("Segoe UI", 14, "bold"), fg=fg_white, bg=bg_card)
        title_lbl.pack(anchor="w")
        sub_lbl = tk.Label(header, text="Encrypted peer-to-peer LAN clipboard sync", font=("Segoe UI", 9), fg=fg_muted, bg=bg_card)
        sub_lbl.pack(anchor="w")

        # Main Scrollable / Content Container
        content = tk.Frame(self.root, bg=bg_main, padx=20, pady=12)
        content.pack(fill="both", expand=True)

        # Section 1: This Computer's IP
        sec1 = tk.LabelFrame(content, text=" This Computer's IP Info ", font=("Segoe UI", 9, "bold"),
                             fg=fg_white, bg=bg_card, bd=1, relief="solid", padx=12, pady=10)
        sec1.pack(fill="x", pady=(0, 10))

        local_ips = ConfigManager.get_local_ips()
        ip_display = ", ".join(local_ips) if local_ips else "No network detected"
        primary_ip = local_ips[0] if local_ips else "127.0.0.1"

        ip_lbl = tk.Label(sec1, text=f"Local IPs: {ip_display}", font=("Segoe UI", 9), fg="#38bdf8", bg=bg_card, wraplength=380, justify="left")
        ip_lbl.pack(side="left", fill="x", expand=True)

        def copy_ip():
            self.root.clipboard_clear()
            self.root.clipboard_append(primary_ip)
            copy_btn.config(text="✓ Copied!")
            self.root.after(1500, lambda: copy_btn.config(text="📋 Copy IP"))

        copy_btn = tk.Button(sec1, text="📋 Copy IP", font=("Segoe UI", 8, "bold"), bg="#334155", fg=fg_white,
                             activebackground="#475569", activeforeground=fg_white, bd=0, padx=8, pady=4, cursor="hand2", command=copy_ip)
        copy_btn.pack(side="right")

        # Section 2: Target Peer Machine
        sec2 = tk.LabelFrame(content, text=" Target Peer (The Other Computer) ", font=("Segoe UI", 9, "bold"),
                             fg=fg_white, bg=bg_card, bd=1, relief="solid", padx=12, pady=10)
        sec2.pack(fill="x", pady=(0, 10))

        # Peer IP
        peer_ip_row = tk.Frame(sec2, bg=bg_card)
        peer_ip_row.pack(fill="x", pady=2)
        tk.Label(peer_ip_row, text="Peer IP Address:", font=("Segoe UI", 9), fg=fg_white, bg=bg_card, width=15, anchor="w").pack(side="left")
        self.peer_ip_var = tk.StringVar(value=self.cfg_mgr.get("peer_ip", ""))
        peer_ip_entry = tk.Entry(peer_ip_row, textvariable=self.peer_ip_var, font=("Consolas", 10), bg="#0f172a", fg=fg_white, insertbackground="white", bd=1)
        peer_ip_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        # Peer Port
        port_row = tk.Frame(sec2, bg=bg_card)
        port_row.pack(fill="x", pady=4)
        tk.Label(port_row, text="Port (Both PCs):", font=("Segoe UI", 9), fg=fg_white, bg=bg_card, width=15, anchor="w").pack(side="left")
        self.port_var = tk.StringVar(value=str(self.cfg_mgr.get("my_port", 58888)))
        port_entry = tk.Entry(port_row, textvariable=self.port_var, font=("Consolas", 10), bg="#0f172a", fg=fg_white, insertbackground="white", bd=1, width=10)
        port_entry.pack(side="left")

        # Ping Button & Status Label
        ping_row = tk.Frame(sec2, bg=bg_card)
        ping_row.pack(fill="x", pady=(6, 0))
        self.ping_status_lbl = tk.Label(ping_row, text="Status: Untested", font=("Segoe UI", 8), fg=fg_muted, bg=bg_card, anchor="w")
        self.ping_status_lbl.pack(side="left", fill="x", expand=True)

        def do_ping():
            self.ping_status_lbl.config(text="Connecting...", fg="#fbbf24")
            def _worker():
                try:
                    port = int(self.port_var.get().strip())
                except ValueError:
                    self.ping_status_lbl.config(text="Invalid port number", fg="#f87171")
                    return
                ip = self.peer_ip_var.get().strip()
                ok, msg, _ = NetworkClient.ping_peer(ip, port)
                if ok:
                    self.ping_status_lbl.config(text=f"✓ {msg}", fg="#4ade80")
                else:
                    self.ping_status_lbl.config(text=f"✗ {msg}", fg="#f87171")
            threading.Thread(target=_worker, daemon=True).start()

        test_btn = tk.Button(ping_row, text="📡 Test Connection", font=("Segoe UI", 8, "bold"), bg="#0369a1", fg=fg_white,
                             activebackground=accent_blue, activeforeground=fg_white, bd=0, padx=10, pady=4, cursor="hand2", command=do_ping)
        test_btn.pack(side="right")

        # Section 3: Encryption / Shared Secret
        sec3 = tk.LabelFrame(content, text=" Security & Encryption (AES) ", font=("Segoe UI", 9, "bold"),
                             fg=fg_white, bg=bg_card, bd=1, relief="solid", padx=12, pady=10)
        sec3.pack(fill="x", pady=(0, 10))

        sec3_row = tk.Frame(sec3, bg=bg_card)
        sec3_row.pack(fill="x", pady=2)
        tk.Label(sec3_row, text="Shared Secret:", font=("Segoe UI", 9), fg=fg_white, bg=bg_card, width=15, anchor="w").pack(side="left")
        self.secret_var = tk.StringVar(value=self.cfg_mgr.get("secret_key", "ClipBeamSecret2026"))
        self.secret_entry = tk.Entry(sec3_row, textvariable=self.secret_var, font=("Consolas", 10), bg="#0f172a", fg=fg_white,
                                     insertbackground="white", bd=1, show="*")
        self.secret_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.show_pass_var = tk.BooleanVar(value=False)
        def toggle_pass():
            self.secret_entry.config(show="" if self.show_pass_var.get() else "*")
        show_cb = tk.Checkbutton(sec3_row, text="Show", variable=self.show_pass_var, font=("Segoe UI", 8),
                                 fg=fg_muted, bg=bg_card, selectcolor="#0f172a", activebackground=bg_card,
                                 activeforeground=fg_white, command=toggle_pass)
        show_cb.pack(side="right")

        desc_lbl = tk.Label(sec3, text="Both machines must use the exact same secret passphrase to decrypt data.",
                            font=("Segoe UI", 8), fg=fg_muted, bg=bg_card)
        desc_lbl.pack(anchor="w", pady=(4, 0))

        # Section 4: Hotkey & Sync Options
        sec4 = tk.LabelFrame(content, text=" Shortcut & Sync Behavior ", font=("Segoe UI", 9, "bold"),
                             fg=fg_white, bg=bg_card, bd=1, relief="solid", padx=12, pady=10)
        sec4.pack(fill="x", pady=(0, 10))

        hk_row = tk.Frame(sec4, bg=bg_card)
        hk_row.pack(fill="x", pady=2)
        tk.Label(hk_row, text="Beam Hotkey:", font=("Segoe UI", 9), fg=fg_white, bg=bg_card, width=15, anchor="w").pack(side="left")
        self.mod_ctrl_var = tk.BooleanVar(value="ctrl" in self.cfg_mgr.get("hotkey_modifiers", []))
        self.mod_alt_var = tk.BooleanVar(value="alt" in self.cfg_mgr.get("hotkey_modifiers", []))
        self.mod_shift_var = tk.BooleanVar(value="shift" in self.cfg_mgr.get("hotkey_modifiers", []))
        self.key_var = tk.StringVar(value=self.cfg_mgr.get("hotkey_key", "c").upper())

        for mod_name, var in [("Ctrl", self.mod_ctrl_var), ("Alt", self.mod_alt_var), ("Shift", self.mod_shift_var)]:
            cb = tk.Checkbutton(hk_row, text=mod_name, variable=var, font=("Segoe UI", 8),
                                fg=fg_white, bg=bg_card, selectcolor="#0f172a", activebackground=bg_card, activeforeground=fg_white)
            cb.pack(side="left", padx=2)

        tk.Label(hk_row, text="+", font=("Segoe UI", 9, "bold"), fg=fg_muted, bg=bg_card).pack(side="left", padx=3)
        key_entry = tk.Entry(hk_row, textvariable=self.key_var, font=("Consolas", 10, "bold"), bg="#0f172a", fg=fg_white,
                             insertbackground="white", bd=1, width=4, justify="center")
        key_entry.pack(side="left", padx=2)

        # Checkboxes for toggles
        self.auto_sync_var = tk.BooleanVar(value=self.cfg_mgr.get("auto_sync", False))
        auto_cb = tk.Checkbutton(sec4, text="Auto-sync on Copy (instantly beam whenever you copy text)",
                                 variable=self.auto_sync_var, font=("Segoe UI", 8),
                                 fg=fg_white, bg=bg_card, selectcolor="#0f172a", activebackground=bg_card, activeforeground=fg_white)
        auto_cb.pack(anchor="w", pady=(6, 2))

        self.notif_var = tk.BooleanVar(value=self.cfg_mgr.get("show_notifications", True))
        notif_cb = tk.Checkbutton(sec4, text="Show toast notification when clipboard is beamed / received",
                                  variable=self.notif_var, font=("Segoe UI", 8),
                                  fg=fg_white, bg=bg_card, selectcolor="#0f172a", activebackground=bg_card, activeforeground=fg_white)
        notif_cb.pack(anchor="w", pady=2)

        self.sound_var = tk.BooleanVar(value=self.cfg_mgr.get("play_sound", True))
        sound_cb = tk.Checkbutton(sec4, text="Play audio chime when clipboard is received",
                                  variable=self.sound_var, font=("Segoe UI", 8),
                                  fg=fg_white, bg=bg_card, selectcolor="#0f172a", activebackground=bg_card, activeforeground=fg_white)
        sound_cb.pack(anchor="w", pady=2)

        self.startup_var = tk.BooleanVar(value=self.cfg_mgr.get("start_with_windows", False))
        startup_cb = tk.Checkbutton(sec4, text="Launch automatically on Windows startup",
                                    variable=self.startup_var, font=("Segoe UI", 8),
                                    fg=fg_white, bg=bg_card, selectcolor="#0f172a", activebackground=bg_card, activeforeground=fg_white)
        startup_cb.pack(anchor="w", pady=2)

        # Bottom Action Bar
        bottom_bar = tk.Frame(self.root, bg=bg_main, padx=20, pady=10)
        bottom_bar.pack(fill="x", side="bottom")

        if self.on_check_updates:
            update_btn = tk.Button(bottom_bar, text="⬇️ Check for Updates", font=("Segoe UI", 8, "bold"), bg="#1e293b", fg="#38bdf8",
                                   activebackground="#334155", activeforeground=fg_white, bd=1, relief="solid", padx=10, pady=5, cursor="hand2",
                                   command=self.on_check_updates)
            update_btn.pack(side="left")

        def save_and_close():
            try:
                port = int(self.port_var.get().strip())
                if port < 1024 or port > 65535:
                    raise ValueError("Port must be between 1024 and 65535")
            except ValueError as ve:
                messagebox.showerror("Invalid Port", str(ve), parent=self.root)
                return

            mods = []
            if self.mod_ctrl_var.get(): mods.append("ctrl")
            if self.mod_alt_var.get(): mods.append("alt")
            if self.mod_shift_var.get(): mods.append("shift")
            if not mods:
                mods = ["ctrl", "shift"]

            key = self.key_var.get().strip().lower() or "c"

            new_settings = {
                "my_port": port,
                "peer_port": port,
                "peer_ip": self.peer_ip_var.get().strip(),
                "secret_key": self.secret_var.get().strip() or "ClipBeamSecret2026",
                "hotkey_modifiers": mods,
                "hotkey_key": key,
                "auto_sync": self.auto_sync_var.get(),
                "show_notifications": self.notif_var.get(),
                "play_sound": self.sound_var.get(),
                "start_with_windows": self.startup_var.get()
            }

            self.cfg_mgr.update(new_settings)
            ConfigManager.update_windows_startup(self.startup_var.get())

            if self.on_save_callback:
                self.on_save_callback(new_settings)

            self.close()

        save_btn = tk.Button(bottom_bar, text="✓ Save & Apply", font=("Segoe UI", 9, "bold"), bg=accent_blue, fg=fg_white,
                             activebackground=accent_hover, activeforeground=fg_white, bd=0, padx=16, pady=6, cursor="hand2", command=save_and_close)
        save_btn.pack(side="right", padx=(8, 0))

        cancel_btn = tk.Button(bottom_bar, text="Cancel", font=("Segoe UI", 9), bg="#334155", fg=fg_white,
                               activebackground="#475569", activeforeground=fg_white, bd=0, padx=14, pady=6, cursor="hand2", command=self.close)
        cancel_btn.pack(side="right")

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.mainloop()

    def close(self):
        if self.root:
            try:
                self.root.destroy()
            except Exception:
                pass
            self.root = None
        self._is_open = False

from typing import Optional
