"""Authenticate to a GL.iNet router and call any documented RPC method.

Usage:
    uv run python examples/call.py system.get_status
    uv run python examples/call.py modem.get_config '{"bus":"1-1"}'
    uv run python examples/call.py --host 192.168.8.1 wifi.get_status

Auth comes from --password or the GLINET_PASSWORD env var.
"""

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

from passlib.hash import md5_crypt, sha256_crypt, sha512_crypt

OPENRPC_DIR = Path(__file__).resolve().parent.parent / "openrpc"


def rpc(url, method, params):
    req = urllib.request.Request(
        url,
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": 1
            }
        ).encode(),
        headers={
            "Content-Type": "application/json"
        }
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def crypt_password(password, alg, salt):
    if alg == 1:
        return md5_crypt.using(salt=salt).hash(password)
    if alg == 5:
        return sha256_crypt.using(salt=salt, rounds=5000).hash(password)
    if alg == 6:
        return sha512_crypt.using(salt=salt, rounds=5000).hash(password)
    raise ValueError(f"unsupported crypt alg {alg}")


def login(url, user, password):
    challenge = rpc(url, "challenge", {"username": user})["result"]
    cipher = crypt_password(password, challenge["alg"], challenge["salt"])
    # Some firmware sends a `hash-method` field that overrides the docs' MD5.
    digest = getattr(hashlib, (challenge.get("hash-method") or "md5").lower())
    h = digest(f"{user}:{cipher}:{challenge['nonce']}".encode()).hexdigest()
    return rpc(url, "login", {"username": user, "hash": h})["result"]["sid"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("method", help='e.g. "system.get_status"')
    ap.add_argument("args", nargs="?", help="optional JSON object")
    ap.add_argument("--host", default=os.environ.get("GLINET_HOST", "192.168.8.1"))
    ap.add_argument("--user", default=os.environ.get("GLINET_USER", "root"))
    ap.add_argument("--password", default=os.environ.get("GLINET_PASSWORD"))
    cli = ap.parse_args()

    if not cli.password:
        sys.exit("--password or GLINET_PASSWORD is required")

    module, fn = cli.method.split(".", 1)
    args = json.loads(cli.args) if cli.args else None

    url = f"http://{cli.host}/rpc"
    sid = login(url, cli.user, cli.password)

    params = [sid, module, fn]
    if args is not None:
        params.append(args)
    resp = rpc(url, "call", params)
    json.dump(resp, sys.stdout, indent=2, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
