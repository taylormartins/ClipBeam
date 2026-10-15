"""Thread-safe recent clipboard history storage."""
import threading
import time
from typing import List, Dict, Any, Optional

class HistoryItem:
    def __init__(self, direction: str, text: str, summary: str, peer: str):
        self.direction = direction  # 'sent' or 'received'
        self.text = text
        self.summary = summary
        self.peer = peer
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction": self.direction,
            "summary": self.summary,
            "peer": self.peer,
            "timestamp": self.timestamp,
            "length": len(self.text)
        }

class HistoryManager:
    def __init__(self, max_items: int = 10):
        self.max_items = max_items
        self.items: List[HistoryItem] = []
        self._lock = threading.Lock()

    def add(self, direction: str, text: str, summary: str, peer: str = ""):
        with self._lock:
            # Avoid adding identical consecutive duplicates
            if self.items and self.items[0].text == text:
                return
            item = HistoryItem(direction, text, summary, peer)
            self.items.insert(0, item)
            if len(self.items) > self.max_items:
                self.items.pop()

    def get_all(self) -> List[HistoryItem]:
        with self._lock:
            return list(self.items)

    def get_at_index(self, index: int) -> Optional[HistoryItem]:
        with self._lock:
            if 0 <= index < len(self.items):
                return self.items[index]
            return None

    def clear(self):
        with self._lock:
            self.items.clear()
