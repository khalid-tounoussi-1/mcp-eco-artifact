from __future__ import annotations

import pytest

from common import connect, load_release, run_sql_file
from fixtures.synthetic_release import build


@pytest.fixture
def synthetic(tmp_path):
    """A SYNTHETIC release (see tests/fixtures/synthetic_release.py) and its data directory."""
    release_dir, data_dir = build(tmp_path)
    return load_release(release_dir), data_dir, release_dir


@pytest.fixture
def con(synthetic):
    release, data_dir, _ = synthetic
    connection, _ = connect(release, data_dir, "researcher")
    run_sql_file(connection, "linked_tools.sql")
    run_sql_file(connection, "server_changes.sql")
    return connection
