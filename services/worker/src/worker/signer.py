import hashlib
import secrets
import time
from cryptography.hazmat.primitives.asymmetric import ed25519

DEFAULT_DEV_WORKER_ID = "worker-local-1"
DEFAULT_DEV_KEY_ID = "key-local-1"
DEFAULT_DEV_PRIV_SEED = "272d500ca44a5cd4ad8fa4a4fa09ce35f1e416733ad6f3beaed708887d46cd2d"
DEFAULT_DEV_PUB_KEY = "544f8f03edfc09fab6ab5d7b42351a0eef237ebfee26bc8e87d60d8899a45113"

class WorkerSigner:
    """Handles Ed25519 cryptographic request signing for RIVET scientific workers."""

    def __init__(self, worker_id: str, key_id: str, private_key: ed25519.Ed25519PrivateKey):
        self.worker_id = worker_id
        self.key_id = key_id
        self._private_key = private_key

    @classmethod
    def from_seed_hex(cls, worker_id: str, key_id: str, seed_hex: str) -> "WorkerSigner":
        seed_bytes = bytes.fromhex(seed_hex)
        if len(seed_bytes) != 32:
            raise ValueError(f"seed must be exactly 32 bytes, got {len(seed_bytes)}")
        priv = ed25519.Ed25519PrivateKey.from_private_bytes(seed_bytes)
        return cls(worker_id, key_id, priv)

    @classmethod
    def dev_default(cls) -> "WorkerSigner":
        return cls.from_seed_hex(DEFAULT_DEV_WORKER_ID, DEFAULT_DEV_KEY_ID, DEFAULT_DEV_PRIV_SEED)

    @property
    def public_key_hex(self) -> str:
        return self._private_key.public_key().public_bytes_raw().hex()

    def canonical_string(self, method: str, path: str, timestamp: int, nonce: str, body_sha256: str) -> str:
        return f"{method}\n{path}\n{self.worker_id}\n{self.key_id}\n{timestamp}\n{nonce}\n{body_sha256}"

    def sign_request(self, method: str, path: str, body: bytes = b"") -> dict[str, str]:
        body_sha256 = hashlib.sha256(body).hexdigest()
        timestamp = int(time.time())
        nonce = secrets.token_hex(16)

        canonical = self.canonical_string(method, path, timestamp, nonce, body_sha256)
        sig = self._private_key.sign(canonical.encode("utf-8"))

        return {
            "X-Worker-ID": self.worker_id,
            "X-Key-ID": self.key_id,
            "X-Timestamp": str(timestamp),
            "X-Nonce": nonce,
            "X-Signature": sig.hex(),
        }
