import hashlib, tempfile, os
from worker.sources import is_allowed_host, sha256_file, verify_checksum

def test_host_allowlist():
    assert is_allowed_host("https://data.earthdata.nasa.gov/x", ["data.earthdata.nasa.gov"])
    assert not is_allowed_host("https://evil.example.com/x", ["data.earthdata.nasa.gov"])

def test_checksum():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"hello")
        p = f.name
    try:
        h = hashlib.sha256(b"hello").hexdigest()
        assert sha256_file(p) == h
        assert verify_checksum(p, h)
        assert not verify_checksum(p, "0"*64)
    finally:
        os.unlink(p)
