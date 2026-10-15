"""Encryption and decryption manager for ClipBeam using Fernet & zlib."""
import base64
import hashlib
import json
import time
import os
import zlib
from typing import Optional, Dict, Any, Tuple
from cryptography.fernet import Fernet, InvalidToken

class CryptoManager:
    @staticmethod
    def _derive_fernet_key(passphrase: str) -> bytes:
        """Derive a URL-safe base64-encoded 32-byte key from any passphrase."""
        if not passphrase:
            passphrase = "ClipBeamDefaultPassphrase"
        digest = hashlib.sha256(passphrase.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)

    @classmethod
    def encrypt_payload(cls, text: str, passphrase: str, metadata: Optional[Dict[str, Any]] = None) -> bytes:
        """
        Bundle text with metadata, compress with zlib, and encrypt with Fernet.
        Returns ciphertext bytes ready for network transmission.
        """
        payload = {
            "v": 1,
            "sender": os.environ.get("COMPUTERNAME", "PC"),
            "timestamp": time.time(),
            "text": text,
            "meta": metadata or {}
        }
        json_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        compressed = zlib.compress(json_bytes, level=6)
        fernet = Fernet(cls._derive_fernet_key(passphrase))
        return fernet.encrypt(compressed)

    @classmethod
    def decrypt_payload(cls, ciphertext: bytes, passphrase: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]], str]:
        """
        Decrypt and decompress payload.
        Returns: (success: bool, text: Optional[str], metadata: Optional[dict], error_msg: str)
        """
        try:
            fernet = Fernet(cls._derive_fernet_key(passphrase))
            compressed = fernet.decrypt(ciphertext)
            json_bytes = zlib.decompress(compressed)
            payload = json.loads(json_bytes.decode("utf-8"))
            
            text = payload.get("text", "")
            return True, text, payload, ""
        except InvalidToken:
            return False, None, None, "Decryption failed: incorrect encryption key/passphrase."
        except zlib.error:
            return False, None, None, "Decompression failed: corrupted payload."
        except Exception as e:
            return False, None, None, f"Payload error: {str(e)}"
