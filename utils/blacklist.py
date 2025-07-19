import os
import json
from typing import Set, Dict

BLACKLIST_DIR = 'data'
BLACKLIST_FILE = os.path.join(BLACKLIST_DIR, 'blacklist.json')
FAILURE_THRESHOLD = 3

class PersistentBlacklist:
    def __init__(self, path: str = BLACKLIST_FILE, threshold: int = FAILURE_THRESHOLD):
        self.path = path
        self.threshold = threshold
        self.domains: Set[str] = set()
        self.failures: Dict[str, int] = {}
        self._ensure_dir()
        self.load()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.domains = set(data.get('blacklist', []))
                    self.failures = data.get('failures', {})
            except Exception:
                self.domains = set()
                self.failures = {}
        else:
            self.domains = set()
            self.failures = {}

    def save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({'blacklist': list(self.domains), 'failures': self.failures}, f, indent=2)

    def is_blacklisted(self, domain: str) -> bool:
        return domain.lower() in self.domains

    def record_failure(self, domain: str):
        domain = domain.lower()
        self.failures[domain] = self.failures.get(domain, 0) + 1
        if self.failures[domain] >= self.threshold:
            self.domains.add(domain)

    def summary(self):
        return list(self.domains) 