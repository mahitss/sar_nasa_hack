import hashlib
from urllib.parse import urlparse

def is_allowed_host(url: str, allowed: list[str]) -> bool:
    host = urlparse(url).hostname or ""
    return host in allowed

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def verify_checksum(path: str, expected: str) -> bool:
    return sha256_file(path).lower() == expected.lower()
