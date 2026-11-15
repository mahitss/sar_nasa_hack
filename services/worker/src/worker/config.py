import os
from dataclasses import dataclass

@dataclass
class Config:
    allowed_hosts: list[str]
    timeout_seconds: int = 30

def load_config() -> Config:
    hosts = os.getenv("RIVET_ALLOWED_HOSTS", "data.earthdata.nasa.gov,urs.earthdata.nasa.gov,asf.alaska.edu")
    return Config(allowed_hosts=[h.strip() for h in hosts.split(",") if h.strip()], timeout_seconds=int(os.getenv("RIVET_TIMEOUT", "30")))
