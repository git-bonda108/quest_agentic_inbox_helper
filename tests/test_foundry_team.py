"""Reading the platform's content-filter refusal. No model is called."""

from __future__ import annotations

from inbox_helper.foundry_team import blocked_categories

REFUSAL = {
    "code": "content_filter",
    "content_filters": [
        {
            "blocked": False,
            "source_type": "completion",
            "content_filter_results": {"hate": {"filtered": False, "severity": "safe"}},
        },
        {
            "blocked": True,
            "source_type": "prompt",
            "content_filter_results": {
                "violence": {"filtered": False, "severity": "safe"},
                "jailbreak": {"detected": True, "filtered": True},
            },
        },
    ],
}


def test_the_filtered_categories_are_named() -> None:
    assert blocked_categories(REFUSAL) == ["jailbreak"]


def test_an_unreadable_refusal_is_still_a_refusal() -> None:
    assert blocked_categories({"code": "content_filter"}) == ["unspecified"]
    assert blocked_categories(None) == ["unspecified"]
