"""Download tables of the pinned MCP-Eco release from Hugging Face.

The script prints the files of the chosen group and their total size, taken
from release/release-files.json, before it downloads anything. Each file is
checked against its pinned size and SHA-256 hash. Files already present are
verified and never overwritten. No credentials are needed.

Groups: listing, engineer, researcher, all. Use --list to see their sizes.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    DEFAULT_DATA_DIR,
    GROUP_NAMES,
    ArtifactError,
    Release,
    load_release,
    run,
    sha256_file,
    table_path,
    verify_file,
)

# Small release files that pin the revision. Their hashes are in source.json.
REMOTE_EVIDENCE = (("collection_metadata.json", "metadata_sha256"), ("schema.sql", "schema_sha256"))


def human(size: int) -> str:
    for unit in ("B", "KB", "MB"):
        if size < 1000:
            return f"{size:,.1f} {unit}"
        size /= 1000
    return f"{size:,.2f} GB"


def print_groups(release: Release) -> None:
    print(f"Release {release.repo_id} at revision {release.revision}")
    print(f"{'group':<11} {'files':>5} {'download size':>15}  tables")
    for name in GROUP_NAMES:
        tables = release.group(name)
        listed = "every table" if name == "all" else ", ".join(tables)
        print(f"{name:<11} {len(tables):>5} {human(release.size(tables)):>15}  {listed}")
    print("Sizes are decimal (1 MB = 1,000,000 bytes), from release/release-files.json.")


def check_remote_manifest(release: Release, tables) -> None:
    """Compare the remote files at the pinned revision with the pinned manifest."""
    from huggingface_hub import HfApi
    from huggingface_hub.errors import HfHubHTTPError

    paths = [release.files[t]["path"] for t in tables]
    try:
        remote = HfApi().get_paths_info(
            release.repo_id, paths, repo_type="dataset", revision=release.revision
        )
    except HfHubHTTPError as error:
        raise ArtifactError(f"Could not read revision {release.revision} of {release.repo_id}: {error}")
    found = {item.path: item for item in remote}
    for table in tables:
        entry = release.files[table]
        item = found.get(entry["path"])
        if item is None:
            raise ArtifactError(f"{entry['path']} is absent at revision {release.revision}")
        lfs_sha256 = item.lfs.sha256 if item.lfs else None
        if (item.size, lfs_sha256, item.blob_id) != (entry["size"], entry["lfs_sha256"], entry["blob_id"]):
            raise ArtifactError(f"Remote {entry['path']} does not match the pinned manifest")


def download(release: Release, filename: str, data_dir: Path) -> Path:
    from huggingface_hub import hf_hub_download

    return Path(
        hf_hub_download(
            release.repo_id,
            filename,
            repo_type="dataset",
            revision=release.revision,
            local_dir=data_dir,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--group", choices=GROUP_NAMES, help="tables to download")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="default: <repository>/data")
    parser.add_argument("--offline", action="store_true", help="verify local files only, never contact Hugging Face")
    parser.add_argument("--list", action="store_true", help="print the groups and their sizes, then stop")
    args = parser.parse_args()

    release = load_release()
    if args.list:
        print_groups(release)
        return
    if not args.group:
        parser.error("choose --group or --list")

    tables = release.group(args.group)
    present = [t for t in tables if table_path(args.data_dir, t).is_file()]
    missing = [t for t in tables if t not in present]
    print(f"Release {release.repo_id} at revision {release.revision}")
    print(f"Group {args.group!r}: {len(tables)} files, {human(release.size(tables))} in total")
    width = max(len(release.files[t]["path"]) for t in tables)
    for table in tables:
        status = "present, will verify" if table in present else "to download"
        print(f"  {release.files[table]['path']:<{width}}  {human(release.files[table]['size']):>10}  {status}")
    print(f"To download now: {len(missing)} files, {human(release.size(missing))}")

    if args.offline and missing:
        raise ArtifactError(
            f"Offline mode and {len(missing)} file(s) are missing: {', '.join(missing)}. "
            "Run again without --offline to download them."
        )
    for table in present:
        verify_file(release, args.data_dir, table)
    if not args.offline:
        check_remote_manifest(release, tables)
        for filename, key in REMOTE_EVIDENCE:
            if sha256_file(download(release, filename, args.data_dir)) != release.source[key]:
                raise ArtifactError(f"Remote {filename} at the pinned revision does not match release/source.json")
        for table in missing:
            print(f"Downloading parquet/{table}.parquet ...", flush=True)
            path = download(release, release.files[table]["path"], args.data_dir)
            if path.resolve() != table_path(args.data_dir, table).resolve():
                raise ArtifactError(f"Unexpected download location {path}")
            try:
                verify_file(release, args.data_dir, table)
            except ArtifactError:
                path.unlink()  # created by this run, so removing it is safe
                raise

    print(
        f"Verified {len(tables)} of {len(release.tables)} release files (size and SHA-256) "
        f"in {args.data_dir / 'parquet'}"
    )
    if args.group != "all":
        print("This is a subset of the release. scripts/verify_release.py --check verifies the complete release.")


if __name__ == "__main__":
    run(main)
