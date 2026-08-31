"""Thread-safe in-memory MVP storage."""
from threading import RLock
from backend.schemas import AuditDto, JobDto

class MemoryStore:
    def __init__(self) -> None:
        self.audits: dict[str, AuditDto] = {}
        self.jobs: dict[str, JobDto] = {}
        self.lock = RLock()

STORE = MemoryStore()
