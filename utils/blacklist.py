import json
import logging
import os
from typing import Dict, List, Set

BLACKLIST_DIR = "data"
BLACKLIST_FILE = os.path.join(BLACKLIST_DIR, "blacklist.json")
FAILURE_THRESHOLD = 3


class PersistentBlacklist:
    """Tracks domains that repeatedly fail and persists them across runs."""

    def __init__(self, path: str = BLACKLIST_FILE, threshold: int = FAILURE_THRESHOLD) -> None:
        self.path = path
        self.threshold = threshold
        self.domains: Set[str] = set()
        self.failures: Dict[str, int] = {}
        self._ensure_dir()
        self.load()

    def _ensure_dir(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.domains = set(data.get("blacklist", []))
                self.failures = data.get("failures", {})
        except (json.JSONDecodeError, OSError) as e:
            logging.warning(f"Failed to load blacklist from {self.path}: {e}")
            self.domains = set()
            self.failures = {}

    def save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"blacklist": sorted(self.domains), "failures": self.failures}, f, indent=2)

    def is_blacklisted(self, domain: str) -> bool:
        return domain.lower() in self.domains

    def record_failure(self, domain: str) -> None:
        domain = domain.lower()
        self.failures[domain] = self.failures.get(domain, 0) + 1
        if self.failures[domain] >= self.threshold:
            self.domains.add(domain)

    def summary(self) -> List[str]:
        return sorted(self.domains)
