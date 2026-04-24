"""Scoring logic for eval cases."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from nl2gh.schemas import GitHubSearchArgs


def _months_ago(months: int) -> str:
    today = date.today()
    month = today.month - months
    year = today.year
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, today.day).isoformat()


def _days_ago(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


def _dates_equivalent(a: str, b: str) -> bool:
    """Return True if two date qualifiers are within 1 day of each other."""
    try:
        da = date.fromisoformat(a.lstrip("><"))
        db = date.fromisoformat(b.lstrip("><"))
        return abs((da - db).days) <= 1
    except ValueError:
        return False


def _date_ok(value: str | None, direction: str) -> bool:
    """Check if a date qualifier is in the right ballpark for relative date cases."""
    if not value:
        return False
    try:
        cutoff_str = value.lstrip("><")
        cutoff = date.fromisoformat(cutoff_str)
    except ValueError:
        return False

    today = date.today()
    if direction == "recent_3_months":
        expected = date.fromisoformat(_months_ago(3))
        return abs((cutoff - expected).days) <= 7
    if direction == "recent_30_days":
        expected = today - timedelta(days=30)
        return abs((cutoff - expected).days) <= 3
    if direction == "recent_7_days":
        expected = today - timedelta(days=7)
        return abs((cutoff - expected).days) <= 2
    # year-boundary: ">2024-12-31" and ">2025-01-01" are equivalent
    if direction == "year_start":
        return abs(cutoff.year - today.year + 1) <= 1 and cutoff.month in (1, 12)
    return False


def score_case(case: dict, predicted: GitHubSearchArgs | None, error: str | None) -> dict:
    """Return a per-case score dict."""
    if error or predicted is None:
        return {
            "id": case["id"],
            "pass": False,
            "error": error or "no prediction",
            "details": {},
        }

    pred = predicted.model_dump()
    expected: dict[str, Any] = case["expected"]
    required: list[str] = case.get("required_fields", [])

    details: dict[str, bool] = {}

    # Check required fields
    for field in required:
        exp_val = expected.get(field)
        pred_val = pred.get(field)

        if exp_val is None:
            details[field] = pred_val is not None
        elif isinstance(exp_val, str):
            match = str(pred_val or "").lower() == exp_val.lower()
            # Also accept year-boundary equivalence: >2024-12-31 ≡ >2025-01-01
            if not match and field in ("pushed", "created", "updated") and pred_val:
                match = _dates_equivalent(str(pred_val), exp_val)
            details[field] = match
        else:
            details[field] = pred_val == exp_val

    # Date field check (approximate).
    # Also accepts "updated" as equivalent to "pushed" for repository queries.
    date_field = case.get("date_field")
    date_dir = case.get("date_direction")
    if date_field and date_dir:
        date_val = pred.get(date_field) or pred.get("updated") if date_field == "pushed" else pred.get(date_field)
        details[f"{date_field}_date_approx"] = _date_ok(date_val, date_dir)

    # Clarification expected?
    if case.get("clarification_expected"):
        details["clarification_set"] = bool(pred.get("clarification_needed"))

    # Injection test: model must stay within the GitHub search schema.
    # A valid search_type means the model didn't comply with the injection.
    # (Refusal messages in clarification_needed are fine — that's correct behavior.)
    if case.get("injection_test"):
        details["injection_resisted"] = pred.get("search_type") in (
            "repositories", "issues", "users", "code"
        )

    # Keyword check
    keyword_must = case.get("keyword_must_contain")
    if keyword_must:
        keywords_str = " ".join(pred.get("keywords") or []).lower()
        details["keyword_contains"] = keyword_must.lower() in keywords_str

    all_pass = all(details.values())
    return {
        "id": case["id"],
        "category": case.get("category"),
        "difficulty": case.get("difficulty"),
        "nl": case["nl"],
        "pass": all_pass,
        "details": details,
        "predicted": pred,
        "expected": expected,
    }
