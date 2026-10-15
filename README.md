# ⚡ ClipBeam

**Encrypted Peer-to-Peer LAN Clipboard Beamer for Windows**

ClipBeam is a lightweight, zero-latency system tray application designed for developers working across multiple computers (e.g., a personal desktop and a work laptop on corporate VPN). It allows you to beam text, multi-thousand-line code snippets, and terminal logs directly between computers over local Wi-Fi with a single keystroke (`Ctrl + Alt + C`).

No character limits, no clunky Google Chat highlighting, no terminals opening in the background—just instant clipboard-to-clipboard transfer.

---

## ✨ Features

- **⚡ Instant Beam (`Ctrl + Alt + C`)**: Press the hotkey on Computer A, and the text immediately lands in Computer B's clipboard, ready for `Ctrl + V`.
- **🔒 AES-256 Encrypted**: End-to-end encryption using Fernet (AES-128-CBC + HMAC-SHA256) with a pre-shared secret passphrase. Unauthorized packets or mismatched keys are rejected.
- **📦 High-Speed zlib Compression**: Massive 50,000-line server logs compress by 80–90% and beam across your Wi-Fi in milliseconds.
- **🛡️ Corporate VPN Friendly**: Designed to work over local subnets even when one computer is connected to a corporate VPN (like Palo Alto GlobalProtect) where multicast/mDNS is blocked.
- **🪟 Clean System Tray App**: Sits quietly in your Windows notification area. No terminal windows, no console popups.
- **🔔 Windows Notifications & Chimes**: Native Windows toast notification displays the sender, line count, and a text preview.
- **📋 Recent Clips History**: Access and re-copy previous clips directly from the right-click tray menu.
- **🔄 Auto-Sync Mode (Optional)**: Toggle "Auto-sync on Copy" in the tray menu if you prefer automatic clipboard syncing without hotkeys.
- **🚀 Single Standalone `.exe`**: No Python, no dependencies, and no installer needed on your work computer.

---

## 🚀 Quick Start (2-Minute Setup)

### 1. Download ClipBeam
Download **`ClipBeam.exe`** on both of your computers from the [Releases](https://github.com/taylormartins/ClipBeam/releases) page.

### 2. Launch on Computer 1 (e.g. Personal PC)
1. Double-click `ClipBeam.exe`. It will appear in your Windows system tray (bottom-right near the clock).
2. Right-click the **ClipBeam tray icon** ⚡ and select **⚙️ Settings...**.
3. Under **"This Computer's IP Info"**, click **📋 Copy IP** (e.g., `192.168.0.63`).

### 3. Launch on Computer 2 (e.g. Work PC)
1. Double-click `ClipBeam.exe`.
2. Right-click the **ClipBeam tray icon** ⚡ and select **⚙️ Settings...**.
3. In **"Peer IP Address"**, paste the IP of Computer 1.
4. Click **📋 Copy IP** to get Computer 2's IP.

### 4. Link & Verify
1. On Computer 1, enter Computer 2's IP into **"Peer IP Address"**.
2. Make sure the **"Shared Secret"** passphrase is identical on both machines.
3. Click **📡 Test Connection**. You should see a green checkmark: `✓ Online! Connected to 'PC-NAME'`.
4. Click **✓ Save & Apply**.

### 5. You're Ready!
- Copy any text or terminal log on either computer.
- Press **`Ctrl + Alt + C`**.
- The other computer will chime and display a toast notification with the log preview.
- Press **`Ctrl + V`** on the other computer to paste immediately!

---

## ⚙️ Configuration & Customization

Through the **Settings** window or tray menu, you can customize:

| Option | Default | Description |
|---|---|---|
| **Hotkey** | `Ctrl + Alt + C` | Global shortcut to beam current clipboard |
| **Port** | `58888` | Local and peer TCP port (change if conflicting) |
| **Shared Secret** | `ClipBeamSecret2026` | Passphrase used to derive the AES encryption key |
| **Auto-Sync** | `Disabled` | Automatically beam whenever clipboard text changes |
| **Notifications** | `Enabled` | Windows toast notifications for sent/received clips |
| **Audio Chime** | `Enabled` | Plays subtle Windows sound on received clips |
| **Start with Windows**| `Disabled` | Automatically boots ClipBeam on Windows login |

Settings are saved locally to `clipbeam_config.json`.

---

## 🌐 Troubleshooting & VPN Setup

### GlobalProtect / Corporate VPN
If your work computer runs GlobalProtect or another enterprise VPN:
1. Ensure both computers are connected to the same local Wi-Fi router.
2. In ClipBeam Settings, always use the local subnet IP (usually starting with `192.168.x.x` or `10.x.x.x`), **not** the VPN virtual adapter IP. ClipBeam automatically prioritizes local LAN IPs in the IP display.
3. Click **📡 Test Connection** to verify direct connectivity.

### Windows Firewall
The first time you run `ClipBeam.exe`, Windows Defender Firewall may display a prompt asking to allow network access.
- Check the box for **Private networks (home or work network)** and click **Allow access**.
- If connection tests fail, verify port `58888` is not blocked by local third-party firewalls.

---

## 🛠️ Building from Source

If you prefer to run or build from Python source:

### Prerequisites
- Python 3.10+
- Windows 10 or 11

### Setup
```bash
git clone https://github.com/taylormartins/ClipBeam.git
cd ClipBeam

# Install dependencies
python -m pip install -r requirements.txt

# Run directly
python main.py
```

### Build Standalone Executable
```bash
python build_exe.py
```
The compiled single-file `ClipBeam.exe` will be generated in `dist/ClipBeam.exe`.

---

## 📄 License
MIT License. Free for personal and commercial use.
