"""Counting rules of the queries, on SYNTHETIC records only."""

from __future__ import annotations

from checks import observations_by_source
from common import fetch, plain
from fixtures.synthetic_release import sid
from paper_listing import compare, listing

SEARCH = "SELECT * FROM search_linked_tools(?) ORDER BY linked_repositories DESC, tool_name, source, server_id"
PRS = "SELECT * FROM server_pr_search(?, ?) ORDER BY pr_key"


def test_duplicate_declarations_count_once_per_pair(con):
    counts = {r["server_name"]: r["configured_repositories"] for r in listing(con)}
    # alpha is declared by repository 1 in two files and by repository 2 in one.
    assert counts["alpha"] == 2


def test_unmatched_declarations_are_excluded(con):
    rows = listing(con)
    assert all(r["server_id"] != "None" for r in rows)
    assert {r["server_name"] for r in rows} == {"alpha", "beta", "delta"}
    assert sum(r["configured_repositories"] for r in rows) == 4  # distinct matched pairs


def test_listing_order_breaks_ties_by_server_id(con):
    rows = listing(con)
    assert rows[0]["server_name"] == "alpha"
    tied = [r["server_id"] for r in rows[1:]]
    assert tied == sorted(tied)


def test_listing_comparison_reports_key_and_count_differences(con):
    rows = listing(con)
    expected = {r["server_id"]: (r["server_name"], r["configured_repositories"]) for r in rows}
    assert compare(rows, expected) == []
    changed = dict(expected)
    changed[sid("S1")] = ("alpha", 3)
    del changed[sid("S2")]
    problems = compare(rows, changed)
    assert any("expected ('alpha', 3)" in p for p in problems)
    assert any(p.startswith("unexpected server_id") for p in problems)
    assert any("duplicate server_id" in p for p in compare(rows + rows[:1], expected))


def test_tool_search_does_not_multiply_tools_by_repositories(con):
    rows = plain(fetch(con, SEARCH, ["web search"]))
    alpha = [r for r in rows if r["server_id"] == sid("S1")]
    # Two web_search observations, two linked repositories, three declarations.
    assert len(alpha) == 2
    assert {r["linked_repositories"] for r in alpha} == {2}
    assert len(rows) == 3


def test_tool_search_keeps_capability_sources_separate(con):
    rows = fetch(con, SEARCH, ["web_search"])
    assert sorted(r["source"] for r in rows if r["tool_name"] == "web_search") == ["glama", "probe"]


def test_tool_search_setup_example_is_deterministic(con):
    rows = plain(fetch(con, SEARCH, ["web_search"]))
    assert {(r["example_consumer_url"], r["example_config_file_path"]) for r in rows} == {
        ("https://github.com/synthetic/r1", ".cursor/mcp.json")
    }


def test_missing_observations_are_not_zero(con):
    assert observations_by_source(con, sid("S1")) == {"glama": 2, "probe": 1}
    assert "probe" not in observations_by_source(con, sid("S2"))
    assert observations_by_source(con, sid("S3")) == {}


def pr_search(con, server: str, term: str = "query") -> dict[str, dict]:
    rows = fetch(con, PRS, [sid(server), term])
    by_url = {r["pr_key"].rsplit("/", 1)[1]: r for r in rows}
    assert len(by_url) == len(rows)
    return by_url


def pr_key(con, url: str) -> str:
    return fetch(con, "SELECT pr_key(?) AS k", [url])[0]["k"]


def test_pr_key_folds_case_and_drops_tree_segments(con):
    assert pr_key(con, "https://github.com/Owner/Repo/tree/main/pkg/pull/7") == "https://github.com/owner/repo/pull/7"
    assert pr_key(con, "https://github.com/owner/repo/pull/7") == "https://github.com/owner/repo/pull/7"


def test_pr_key_does_not_merge_different_pull_requests(con):
    # The /tree/ segment is dropped only right after owner/repo.
    assert pr_key(con, "https://github.com/tree/a/pull/3") != pr_key(con, "https://github.com/tree/b/pull/3")
    assert pr_key(con, "https://github.com/o/tree/tree/head/x/pull/3") == "https://github.com/o/tree/pull/3"
    # Other hosts are left unchanged.
    assert pr_key(con, "https://gitlab.com/A/B/pull/1") == "https://gitlab.com/A/B/pull/1"


def test_pr_search_returns_one_row_per_pull_request(con):
    # pull/4 is stored twice, pull/8 also in the client table, and pull/9
    # under two spellings: still one row each.
    assert set(pr_search(con, "S1")) == {"1", "2", "3", "4", "8", "9"}


def test_pr_search_gathers_url_spellings_and_their_reviews(con):
    pr = pr_search(con, "S1")["9"]
    assert pr["pr_urls"] == ["https://github.com/synthetic/S1/pull/9", "https://github.com/synthetic/s1/tree/main/pkg/pull/9"]
    assert pr["pr_ids"] == [109, 110]
    assert (pr["review_rows"], pr["approved_review_rows"]) == (1, 1)


def test_pr_search_counts_reviews_per_pull_request(con):
    pr = pr_search(con, "S1")["1"]
    assert (pr["review_rows"], pr["approved_review_rows"]) == (2, 1)


def test_pr_search_gathers_twin_rows_and_their_reviews(con):
    pr = pr_search(con, "S1")["4"]
    assert pr["pr_ids"] == [104, 105]
    assert (pr["server_rows"], pr["client_rows"]) == (2, 0)
    assert pr["states"] == ["CLOSED", "OPEN"]  # stored rows disagree, both kept
    assert (pr["review_rows"], pr["approved_review_rows"]) == (2, 1)


def test_twin_is_the_same_pull_request_from_either_server(con):
    from_s1, from_s4 = pr_search(con, "S1")["4"], pr_search(con, "S4")["4"]
    assert from_s1 == from_s4


def test_pr_search_gathers_reviews_under_client_ids(con):
    pr = pr_search(con, "S1")["8"]
    assert pr["pr_ids"] == [108, 208]
    assert (pr["server_rows"], pr["client_rows"]) == (1, 1)
    assert (pr["review_rows"], pr["approved_review_rows"]) == (1, 1)


def test_pr_search_withholds_reviews_for_reused_ids(con):
    pr = pr_search(con, "S1")["2"]
    assert pr["review_attribution_clean"] is False
    assert pr["review_rows"] is None


def test_pr_search_keeps_absent_reviews_null(con):
    pr = pr_search(con, "S1")["3"]
    assert pr["review_attribution_clean"] is True
    assert pr["review_rows"] is None
    assert pr["merged_at_values"] == []
