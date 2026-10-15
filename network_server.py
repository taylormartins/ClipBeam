"""Lightweight HTTP server to receive encrypted clipboard beams."""
import json
import socket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Callable, Optional, Tuple
from crypto_manager import CryptoManager
from clipboard_manager import ClipboardManager

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

class ClipBeamRequestHandler(BaseHTTPRequestHandler):
    server: 'ThreadedHTTPServer'

    def log_message(self, format, *args):
        # Suppress default console output
        pass

    def do_GET(self):
        if self.path == "/ping":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "status": "ok",
                "app": "ClipBeam",
                "machine": socket.gethostname()
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/beam":
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length <= 0:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Empty body")
                return

            ciphertext = self.rfile.read(content_length)
            secret_key = getattr(self.server, "get_secret_key", lambda: "")()

            success, text, meta, err = CryptoManager.decrypt_payload(ciphertext, secret_key)
            if not success:
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": err}).encode("utf-8"))
                return

            sender = meta.get("sender", "Unknown Peer") if meta else "Peer"
            summary = ClipboardManager.get_summary(text or "")

            # Dispatch to callback
            dispatch = getattr(self.server, "dispatch_received", None)
            if dispatch:
                dispatch(text or "", sender, summary)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "received", "summary": summary}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

class ClipBeamServer:
    def __init__(self, port: int, get_secret_key: Callable[[], str], on_received: Callable[[str, str, str], None]):
        self.port = port
        self.get_secret_key = get_secret_key
        self.on_received = on_received
        self._server: Optional[ThreadedHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def dispatch_received(self, text: str, sender: str, summary: str):
        if self.on_received:
            self.on_received(text, sender, summary)

    def start(self) -> Tuple[bool, str]:
        if self._running:
            return True, "Server already running"
        try:
            # Bind to 0.0.0.0 so all LAN/VPN adapters can connect
            self._server = ThreadedHTTPServer(("0.0.0.0", self.port), ClipBeamRequestHandler)
            self._server.get_secret_key = self.get_secret_key
            self._server.dispatch_received = self.dispatch_received
            self._running = True

            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True, name="ClipBeamServerThread")
            self._thread.start()
            return True, f"Listening on port {self.port}"
        except Exception as e:
            self._running = False
            return False, f"Failed to bind port {self.port}: {str(e)}"

    def stop(self):
        if self._server:
            try:
                self._server.shutdown()
                self._server.server_close()
            except Exception:
                pass
            self._server = None
        self._running = False
