"""Identity and schema checks of the worked examples, on SYNTHETIC records only."""

from __future__ import annotations

import copy

import pytest

from checks import (
    CheckFailed,
    check_receipt,
    one,
    required_inputs,
    reviews_for,
    unique_server_pr,
    validate_examples,
)
from fixtures.synthetic_release import SCHEMA


def test_unique_pull_request_passes(con):
    pr = unique_server_pr(con, "https://github.com/synthetic/s1/pull/1")
    assert pr["pr_id"] == 101


def test_pr_id_shared_with_client_table_fails(con):
    with pytest.raises(CheckFailed, match="also appears in client_pull_requests"):
        unique_server_pr(con, "https://github.com/synthetic/s1/pull/2")


def test_duplicate_selected_url_fails(con):
    with pytest.raises(CheckFailed, match="expected one record, found 2"):
        unique_server_pr(con, "https://github.com/synthetic/s1/pull/4")


def test_selected_url_with_a_second_spelling_fails(con):
    with pytest.raises(CheckFailed, match="expected one record, found 2"):
        unique_server_pr(con, "https://github.com/synthetic/s1/pull/9")


def test_selected_url_also_stored_as_client_pr_fails(con):
    with pytest.raises(CheckFailed, match="pull/8 also appears in client_pull_requests"):
        unique_server_pr(con, "https://github.com/synthetic/s1/pull/8")


def test_duplicate_pr_id_fails(con):
    with pytest.raises(CheckFailed, match="appears 2 times in server_pull_requests"):
        unique_server_pr(con, "https://github.com/synthetic/s1/pull/6")


def test_one_rejects_empty_and_multiple():
    with pytest.raises(CheckFailed):
        one([], "nothing")
    with pytest.raises(CheckFailed):
        one([{}, {}], "two")


def test_valid_input_passes_and_invalid_inputs_fail():
    validate_examples(SCHEMA, valid=[{"query": "docs"}], invalid=[{"limit": 5}, {"query": 5}])


def test_schema_that_accepts_an_invalid_input_fails_the_check():
    with pytest.raises(CheckFailed, match="accepts invalid input"):
        validate_examples(SCHEMA, valid=[], invalid=[{"query": "this is valid"}])


def test_schema_that_rejects_a_valid_input_fails_the_check():
    with pytest.raises(CheckFailed, match="rejects valid input"):
        validate_examples(SCHEMA, valid=[{"limit": 1}], invalid=[])


def test_missing_schema_is_not_an_empty_input_list():
    assert required_inputs(None) is None
    assert required_inputs(SCHEMA) == ["query"]
    assert required_inputs("{not json") == "unparseable schema"


def receipt_for(pr, reviews):
    return {
        "consumer": {"repository_url": "https://github.com/synthetic/r1", "exa_command": "npx",
                     "exa_package_argument_present": True},
        "pull_request": {"html_url": pr["pr_url"], "issue_id": pr["pr_id"], "pull_id": 1},
        "reviews": [{"id": r["review_id"], "state": r["review_state"]} for r in reviews],
    }


def test_receipt_replay_passes_and_detects_changes(con):
    pr = unique_server_pr(con, "https://github.com/synthetic/s1/pull/1")
    reviews = reviews_for(con, pr["pr_id"])
    receipt = receipt_for(pr, reviews)
    check_receipt(receipt, consumer_url="https://github.com/synthetic/r1", pr=pr, reviews=reviews)

    changed_state = copy.deepcopy(receipt)
    changed_state["reviews"][1]["state"] = "CHANGES_REQUESTED"
    with pytest.raises(CheckFailed, match="review IDs or states"):
        check_receipt(changed_state, consumer_url="https://github.com/synthetic/r1", pr=pr, reviews=reviews)

    other_id = copy.deepcopy(receipt)
    other_id["pull_request"]["issue_id"] = 999
    with pytest.raises(CheckFailed, match="issue ID"):
        check_receipt(other_id, consumer_url="https://github.com/synthetic/r1", pr=pr, reviews=reviews)
