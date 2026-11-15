import argparse
import json
import os
import secrets
import sys

from cryptography.hazmat.primitives.asymmetric import ed25519

from .client import WorkerClient
from .config import load_config
from .processing import inspect_raster, write_manifest, water_candidate_allowed
from .runner import WorkerRunner
from .signer import (
    WorkerSigner,
    DEFAULT_DEV_WORKER_ID,
    DEFAULT_DEV_KEY_ID,
    DEFAULT_DEV_PRIV_SEED,
)
from .sources import is_allowed_host, sha256_file, verify_checksum

def get_client(api_url: str) -> WorkerClient:
    worker_id = os.getenv("RIVET_WORKER_ID", DEFAULT_DEV_WORKER_ID)
    key_id = os.getenv("RIVET_WORKER_KEY_ID", DEFAULT_DEV_KEY_ID)
    seed_hex = os.getenv("RIVET_WORKER_PRIVATE_KEY", DEFAULT_DEV_PRIV_SEED)
    signer = WorkerSigner.from_seed_hex(worker_id, key_id, seed_hex)
    return WorkerClient(base_url=api_url, signer=signer)

def cmd_keygen(args):
    seed = secrets.token_bytes(32)
    priv = ed25519.Ed25519PrivateKey.from_private_bytes(seed)
    pub_hex = priv.public_key().public_bytes_raw().hex()
    out = {
        "private_seed_hex": seed.hex(),
        "public_key_hex": pub_hex,
    }
    print(json.dumps(out, indent=2))

def cmd_claim(args):
    client = get_client(args.api_url)
    job = client.claim_job()
    print(json.dumps({"claimed_job": job}, indent=2))

def cmd_run_once(args):
    client = get_client(args.api_url)
    runner = WorkerRunner(client)
    job = runner.run_once()
    if job:
        print(json.dumps({"status": "executed", "job": job}, indent=2))
    else:
        print(json.dumps({"status": "idle", "message": "no queued jobs found"}))

def cmd_poll(args):
    client = get_client(args.api_url)
    runner = WorkerRunner(client)
    count = runner.poll(interval=args.interval, max_jobs=args.max_jobs)
    print(json.dumps({"status": "stopped", "processed_jobs": count}))

def main(argv=None):
    parser = argparse.ArgumentParser(prog="rivet-worker")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # Existing commands preserved
    p = sub.add_parser("config")
    p.set_defaults(func=lambda a: print(json.dumps({"allowed_hosts": load_config().allowed_hosts})))

    p = sub.add_parser("inspect-raster")
    p.add_argument("path")
    p.set_defaults(func=lambda a: print(inspect_raster(a.path).__dict__))

    p = sub.add_parser("checksum")
    p.add_argument("path")
    p.set_defaults(func=lambda a: print(sha256_file(a.path)))

    p = sub.add_parser("verify-checksum")
    p.add_argument("path")
    p.add_argument("expected")
    p.set_defaults(func=lambda a: print(verify_checksum(a.path, a.expected)))

    p = sub.add_parser("check-host")
    p.add_argument("url")
    p.set_defaults(func=lambda a: print(is_allowed_host(a.url, load_config().allowed_hosts)))

    p = sub.add_parser("water-candidate-check")
    p.add_argument("params_json")
    p.set_defaults(func=lambda a: print(water_candidate_allowed(json.loads(a.params_json))))

    # New Mission 021 worker commands
    p = sub.add_parser("keygen")
    p.set_defaults(func=cmd_keygen)

    p = sub.add_parser("claim")
    p.add_argument("--api-url", default=os.getenv("RIVET_API_URL", "http://127.0.0.1:8080"))
    p.set_defaults(func=cmd_claim)

    p = sub.add_parser("run-once")
    p.add_argument("--api-url", default=os.getenv("RIVET_API_URL", "http://127.0.0.1:8080"))
    p.set_defaults(func=cmd_run_once)

    p = sub.add_parser("poll")
    p.add_argument("--api-url", default=os.getenv("RIVET_API_URL", "http://127.0.0.1:8080"))
    p.add_argument("--interval", type=float, default=5.0)
    p.add_argument("--max-jobs", type=int, default=0)
    p.set_defaults(func=cmd_poll)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
