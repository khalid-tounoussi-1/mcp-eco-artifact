"""Release identity, download and verification failures.

Uses the real pinned manifest for group sizes and SYNTHETIC files for every
check that needs Parquet data. No test contacts Hugging Face.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys

import pytest

import download_data
import verify_release
from common import ROOT, ArtifactError, connect, load_release, table_path, verify_file
from fixtures.synthetic_release import rehash


def test_groups_are_nested_and_sized_from_the_manifest():
    release = load_release()
    listing, engineer, researcher, everything = (release.group(g) for g in ("listing", "engineer", "researcher", "all"))
    assert set(listing) < set(engineer) < set(researcher) < set(everything)
    assert len(everything) == 19
    assert release.size(listing) == sum(release.files[t]["size"] for t in listing)
    assert "commits" not in researcher  # large history tables stay out of the examples


def test_altered_manifest_fails_before_analysis(synthetic, tmp_path):
    _, _, release_dir = synthetic
    manifest = json.loads((release_dir / "release-files.json").read_text())
    manifest[0]["size"] += 1
    (release_dir / "release-files.json").write_text(json.dumps(manifest))
    with pytest.raises(ArtifactError, match="Pinned evidence file has changed"):
        load_release(release_dir)


def test_branch_name_instead_of_commit_fails(synthetic):
    _, _, release_dir = synthetic
    source = json.loads((release_dir / "source.json").read_text())
    source["revision"] = "main"
    (release_dir / "source.json").write_text(json.dumps(source))
    with pytest.raises(ArtifactError, match="full 40-character commit hash"):
        load_release(release_dir)


def test_metadata_and_manifest_must_agree(synthetic):
    _, _, release_dir = synthetic
    manifest = json.loads((release_dir / "release-files.json").read_text())
    (release_dir / "release-files.json").write_text(json.dumps(manifest[:-1]))
    rehash(release_dir)  # consistent hashes, inconsistent contents
    with pytest.raises(ArtifactError, match="disagree"):
        load_release(release_dir)


def test_bad_hash_with_correct_size_fails(synthetic):
    release, data_dir, _ = synthetic
    path = table_path(data_dir, "mcp_servers")
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 0xFF
    path.write_bytes(bytes(data))
    with pytest.raises(ArtifactError, match="SHA-256"):
        verify_file(release, data_dir, "mcp_servers")
    with pytest.raises(ArtifactError, match="SHA-256"):
        connect(release, data_dir, "listing")


def test_wrong_size_fails(synthetic):
    release, data_dir, _ = synthetic
    with table_path(data_dir, "mcp_servers").open("ab") as stream:
        stream.write(b"x")
    with pytest.raises(ArtifactError, match="bytes, the pinned release has"):
        verify_file(release, data_dir, "mcp_servers")


def test_missing_table_names_the_download_command(synthetic):
    release, data_dir, _ = synthetic
    table_path(data_dir, "mcp_tools").unlink()
    with pytest.raises(ArtifactError, match="download_data.py --group engineer"):
        connect(release, data_dir, "engineer")


def test_offline_download_with_missing_files_fails_without_traceback(tmp_path):
    result = subprocess.run(
        [sys.executable, "scripts/download_data.py", "--group", "listing", "--data-dir", str(tmp_path), "--offline"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "Offline mode and 2 file(s) are missing" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.fixture
def fake_hub(synthetic, tmp_path, monkeypatch):
    """Serve the SYNTHETIC files as if they were the remote release."""
    release, source_data, release_dir = synthetic
    remote = tmp_path / "remote"
    shutil.copytree(source_data, remote)
    for name in ("collection_metadata.json", "schema.sql"):
        shutil.copy(release_dir / name, remote / name)
    calls = []

    def hf_hub_download(repo_id, filename, *, repo_type, revision, local_dir):
        calls.append((repo_id, filename, repo_type, revision))
        target = local_dir / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(remote / filename, target)
        return str(target)

    import huggingface_hub

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", hf_hub_download)
    monkeypatch.setattr(download_data, "load_release", lambda: release)
    monkeypatch.setattr(download_data, "check_remote_manifest", lambda release, tables: None)
    return release, remote, calls


def run_main(module, monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", [module.__name__, *argv])
    module.main()


def test_download_uses_pinned_repository_and_revision(fake_hub, tmp_path, monkeypatch, capsys):
    release, _, calls = fake_hub
    target = tmp_path / "fresh"
    run_main(download_data, monkeypatch, "--group", "listing", "--data-dir", str(target))
    assert {(c[0], c[2], c[3]) for c in calls} == {(release.repo_id, "dataset", release.revision)}
    out = capsys.readouterr().out
    assert "Verified 2 of 8 release files" in out
    assert "This is a subset of the release" in out


def test_corrupt_download_is_rejected_and_removed(fake_hub, tmp_path, monkeypatch):
    _, remote, _ = fake_hub
    path = remote / "parquet" / "mcp_servers.parquet"
    path.write_bytes(b"\0" * path.stat().st_size)
    target = tmp_path / "fresh"
    with pytest.raises(ArtifactError, match="SHA-256"):
        run_main(download_data, monkeypatch, "--group", "listing", "--data-dir", str(target))
    assert not table_path(target, "mcp_servers").exists()


def test_existing_bad_file_is_not_overwritten(fake_hub, synthetic, monkeypatch):
    _, data_dir, _ = synthetic
    path = table_path(data_dir, "mcp_servers")
    path.write_bytes(b"\0" * path.stat().st_size)
    with pytest.raises(ArtifactError, match="was not changed"):
        run_main(download_data, monkeypatch, "--group", "listing", "--data-dir", str(data_dir))
    assert path.read_bytes() == b"\0" * path.stat().st_size


def test_subset_verification_never_claims_the_complete_release(synthetic, monkeypatch, capsys):
    release, data_dir, _ = synthetic
    monkeypatch.setattr(verify_release, "load_release", lambda: release)
    run_main(verify_release, monkeypatch, "--data-dir", str(data_dir), "--check", "--group", "listing")
    out = capsys.readouterr().out
    assert '"complete_release_verified": false' in out
    assert "The complete release has not been verified" in out
    assert "PASS: all" not in out

    run_main(verify_release, monkeypatch, "--data-dir", str(data_dir), "--check")
    out = capsys.readouterr().out
    assert '"complete_release_verified": true' in out
    assert f"PASS: all {len(release.tables)} files" in out


def test_emit_refuses_a_corrupted_file(synthetic, monkeypatch):
    release, data_dir, _ = synthetic
    path = table_path(data_dir, "mcp_servers")
    path.write_bytes(b"\0" * path.stat().st_size)
    monkeypatch.setattr(verify_release, "load_release", lambda: release)
    with pytest.raises(ArtifactError, match="SHA-256"):
        run_main(verify_release, monkeypatch, "--data-dir", str(data_dir), "--emit", "total_rows")


def test_subset_report_does_not_use_the_total_key(synthetic, monkeypatch, capsys):
    release, data_dir, _ = synthetic
    monkeypatch.setattr(verify_release, "load_release", lambda: release)
    run_main(verify_release, monkeypatch, "--data-dir", str(data_dir), "--check", "--group", "listing")
    report = json.loads(capsys.readouterr().out.split("\nPASS")[0])
    assert "total_rows" not in report and report["subset_rows"] == sum(report["table_row_counts"].values())


def test_claims_ledger_must_cover_every_inventory_number():
    import yaml

    from check_claims import check_ledger

    release = load_release()
    claims = yaml.safe_load((ROOT / "release" / "claims.yaml").read_text())["claims"]
    check_ledger(claims, release.tables)
    with pytest.raises(ArtifactError, match="incomplete"):
        check_ledger([c for c in claims if c["id"] != "rows.commits"], release.tables)
    with pytest.raises(ArtifactError, match="incomplete"):
        check_ledger([], release.tables)
    swapped = [dict(c, cmd="python scripts/verify_release.py --emit total_rows") if c["id"] == "table_count" else c
               for c in claims]
    with pytest.raises(ArtifactError, match="must be `python scripts/verify_release.py --emit table_count`"):
        check_ledger(swapped, release.tables)
    spoofed = [dict(c, cmd='python -c "print(19)" --emit table_count') if c["id"] == "table_count" else c
               for c in claims]
    with pytest.raises(ArtifactError, match="must be"):
        check_ledger(spoofed, release.tables)
    for claim_id, text in (("total_rows", "16{,}880{,}889"), ("export_date", "2026-06-24")):
        mistyped = [dict(c, text=text) if c["id"] == claim_id else c for c in claims]
        with pytest.raises(ArtifactError, match="does not match value"):
            check_ledger(mistyped, release.tables)
