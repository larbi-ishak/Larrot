"""Request journal: an in-memory, bounded log of every request Larrot serves.

WireMock's request journal, adapted: tests can verify what the client
actually sent (method, path, status, duration) and query it via
GET /admin/requests. The journal is a ring buffer - the oldest entries
are dropped - so it can never grow unbounded.
"""

import threading
import time
from collections import deque
from dataclasses import asdict, dataclass, field

DEFAULT_SIZE = 1000


@dataclass
class JournalEntry:
    method: str
    path: str
    status: int
    duration_ms: float
    request_id: str
    matched: bool  # False = no route (APIGW.0101 with near-miss hints)
    near_misses: list = field(default_factory=list)
    time: float = field(default_factory=time.time)


class RequestJournal:
    def __init__(self, maxsize: int = DEFAULT_SIZE):
        self._entries = deque(maxlen=maxsize)
        self._lock = threading.Lock()
        self.total = 0  # requests seen since start (unbounded counter)

    def record(self, **kwargs) -> JournalEntry:
        entry = JournalEntry(**kwargs)
        with self._lock:
            self._entries.append(entry)
            self.total += 1
        return entry

    def query(self, method=None, path=None, status=None, limit=100,
              matched=None) -> list[dict]:
        with self._lock:
            entries = list(self._entries)
        out = []
        for e in reversed(entries):  # newest first
            if method and e.method.upper() != method.upper():
                continue
            if path and path.lower() not in e.path.lower():
                continue
            if status is not None and e.status != status:
                continue
            if matched is not None and e.matched != matched:
                continue
            out.append(asdict(e))
            if len(out) >= limit:
                break
        return out

    def clear(self) -> int:
        with self._lock:
            n = len(self._entries)
            self._entries.clear()
            self.total = 0
        return n

    def __len__(self) -> int:
        return len(self._entries)
