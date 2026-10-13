"""Regenerate every number in release/claims.yaml and fail on drift.

First checks that the ledger has exactly one claim per inventory number
(table count, total, export date, and every table), that the text quoted from
the manuscript matches each value, and that each claim's command is
`python scripts/verify_release.py --emit <its id>`. Then runs
`python scripts/verify_release.py --check`, and finally each claim's command
exactly as written, from the repository root, with this Python interpreter.
--data-dir is appended to every command when given.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

import yaml

from common import RELEASE_DIR, ROOT, ArtifactError, load_release, run


def command(cmd: str, data_dir: Path | None) -> list[str]:
    argv = shlex.split(cmd)
    if argv[0] != "python":
        raise ArtifactError(f"Claim commands must start with 'python': {cmd}")
    argv[0] = sys.executable
    return argv + (["--data-dir", str(data_dir)] if data_dir else [])


def manuscript_text(claim: dict) -> str:
    """How the manuscript writes a claim's value: 16{,}880{,}899 or 2026-06-23."""
    if claim["id"] == "export_date":
        digits = str(claim["value"])
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}"
    return f"{claim['value']:,}".replace(",", "{,}")


def check_ledger(claims: list[dict], tables) -> None:
    """Every inventory number must have exactly one claim, tied to its own metric,
    and the text quoted from the manuscript must match the value."""
    expected = {"table_count", "total_rows", "export_date"} | {f"rows.{t}" for t in tables}
    ids = [c["id"] for c in claims]
    if len(ids) != len(set(ids)):
        raise ArtifactError("Duplicate claim ids in release/claims.yaml")
    if set(ids) != expected:
        missing, extra = sorted(expected - set(ids)), sorted(set(ids) - expected)
        raise ArtifactError(f"release/claims.yaml is incomplete. Missing: {missing}. Unexpected: {extra}.")
    for claim in claims:
        if str(claim["text"]) != manuscript_text(claim):
            raise ArtifactError(f"Claim {claim['id']}: text {claim['text']!r} does not match value {claim['value']}")
        if shlex.split(claim["cmd"]) != ["python", "scripts/verify_release.py", "--emit", claim["id"]]:
            raise ArtifactError(
                f"Claim {claim['id']} must be `python scripts/verify_release.py --emit {claim['id']}`, "
                f"not: {claim['cmd']}"
            )


def execute(argv: list[str]) -> str:
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise ArtifactError(f"{shlex.join(argv)} failed:\n{result.stderr.strip()}")
    return result.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, help="default: <repository>/data")
    args = parser.parse_args()
    data_dir = args.data_dir.resolve() if args.data_dir else None

    ledger = yaml.safe_load((RELEASE_DIR / "claims.yaml").read_text())
    check_ledger(ledger["claims"], load_release().tables)
    print("Verifying the complete release first (hashes all 19 files) ...", flush=True)
    execute(command("python scripts/verify_release.py --check", data_dir))

    drift = []
    for claim in ledger["claims"]:
        observed = execute(command(claim["cmd"], data_dir))
        status = "ok" if observed == str(claim["value"]) else "DRIFT"
        if status == "DRIFT":
            drift.append(claim["id"])
        print(f"{status:<5} {claim['id']:<32} expected {claim['value']:>10}  observed {observed:>10}  ({claim['unit']})")
    if drift:
        raise ArtifactError(f"{len(drift)} claim(s) drifted: {', '.join(drift)}")
    print(f"PASS: {len(ledger['claims'])} claims regenerated from the verified release")


if __name__ == "__main__":
    run(main)
