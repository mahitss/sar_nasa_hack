import argparse
import json
import sys

from .config import load_config
from .processing import inspect_raster, write_manifest, water_candidate_allowed
from .sources import is_allowed_host, sha256_file, verify_checksum

def main(argv=None):
    parser = argparse.ArgumentParser(prog="rivet-worker")
    sub = parser.add_subparsers(dest="cmd", required=True)

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

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
