"""HTTP client for sending clipboard payloads and checking connectivity."""
import time
import json
import urllib.request
import urllib.error
from typing import Tuple, Dict, Any, Optional
from crypto_manager import CryptoManager

class NetworkClient:
    @staticmethod
    def ping_peer(peer_ip: str, peer_port: int, timeout: float = 3.0) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Ping peer machine to verify network reachability.
        Returns: (success: bool, status_message: str, data: Optional[dict])
        """
        if not peer_ip:
            return False, "Target IP is empty. Please set peer IP in Settings.", None

        url = f"http://{peer_ip}:{peer_port}/ping"
        start_time = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ClipBeam-Client/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                latency_ms = int((time.time() - start_time) * 1000)
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    machine = data.get("machine", "Remote PC")
                    return True, f"Online! Connected to '{machine}' ({latency_ms}ms)", data
                return False, f"Unexpected response HTTP {response.status}", None
        except urllib.error.URLError as e:
            return False, f"Could not reach {peer_ip}:{peer_port} ({e.reason})", None
        except socket_timeout_error:
            return False, f"Connection to {peer_ip}:{peer_port} timed out after {timeout}s", None
        except Exception as e:
            return False, f"Connection error: {str(e)}", None

    @staticmethod
    def send_clipboard(peer_ip: str, peer_port: int, secret_key: str, text: str, timeout: float = 5.0) -> Tuple[bool, str]:
        """
        Encrypt text and beam to peer.
        Returns: (success: bool, message: str)
        """
        if not peer_ip:
            return False, "No peer IP configured. Open Settings and enter the other computer's IP."
        if not text:
            return False, "Clipboard is empty or contains no text."

        url = f"http://{peer_ip}:{peer_port}/beam"
        try:
            ciphertext = CryptoManager.encrypt_payload(text, secret_key)
            req = urllib.request.Request(
                url,
                data=ciphertext,
                headers={
                    "Content-Type": "application/octet-stream",
                    "Content-Length": str(len(ciphertext)),
                    "User-Agent": "ClipBeam-Client/1.0"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    return True, f"Successfully beamed to {peer_ip}"
                return False, f"Peer returned HTTP {response.status}"
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return False, "Decryption rejected: Encryption keys do not match!"
            return False, f"Peer HTTP error: {e.code}"
        except urllib.error.URLError as e:
            return False, f"Could not connect to {peer_ip}:{peer_port} ({e.reason})"
        except Exception as e:
            return False, f"Send failed: {str(e)}"

# Alias socket timeout
import socket
socket_timeout_error = socket.timeout
