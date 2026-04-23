import pytest
from nl2gh.executor import GitHubExecutor
from nl2gh.schemas import GitHubSearchArgs


def make_executor() -> GitHubExecutor:
    return GitHubExecutor(token="fake-token-for-unit-tests")


def test_build_query_basic():
    ex = make_executor()
    args = GitHubSearchArgs(search_type="repositories", language="python", stars=">1000")
    q = ex.build_query_string(args)
    assert "language:python" in q
    assert "stars:>1000" in q


def test_build_query_keywords():
    ex = make_executor()
    args = GitHubSearchArgs(search_type="repositories", keywords=["machine-learning", "neural"])
    q = ex.build_query_string(args)
    assert "machine-learning" in q
    assert "neural" in q


def test_build_query_fork_false():
    ex = make_executor()
    args = GitHubSearchArgs(search_type="repositories", language="rust", fork=False)
    q = ex.build_query_string(args)
    assert "fork:false" in q


def test_build_query_location_quoted():
    ex = make_executor()
    args = GitHubSearchArgs(search_type="users", location="San Francisco")
    q = ex.build_query_string(args)
    assert 'location:"San Francisco"' in q


def test_build_query_issue_type():
    ex = make_executor()
    args = GitHubSearchArgs(
        search_type="issues",
        repo="pytorch/pytorch",
        state="open",
        issue_type="issue",
    )
    q = ex.build_query_string(args)
    assert "repo:pytorch/pytorch" in q
    assert "state:open" in q
    assert "type:issue" in q


def test_validate_warns_fork_true():
    ex = make_executor()
    args = GitHubSearchArgs(search_type="repositories", fork=True)
    warnings = ex.validate(args)
    assert any("fork" in w for w in warnings)


def test_validate_warns_bad_date():
    ex = make_executor()
    args = GitHubSearchArgs(search_type="repositories", pushed="2024-01-01")
    warnings = ex.validate(args)
    assert any("pushed" in w for w in warnings)
