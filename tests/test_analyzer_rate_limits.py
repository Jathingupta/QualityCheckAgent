import httpx

from app.analyzer import (
    MAX_BATCH_CHARS,
    MAX_COMPLETION_TOKENS,
    _parse_delay,
    _rate_limit_delay,
)


def test_groq_request_budgets_are_reduced_for_free_tier():
    assert MAX_BATCH_CHARS == 4500
    assert MAX_COMPLETION_TOKENS == 1000


def test_parse_delay_supports_seconds_and_compound_durations():
    assert _parse_delay("2") == 2.0
    assert _parse_delay("7.66s") == 7.66
    assert _parse_delay("2m3.5s") == 123.5
    assert _parse_delay("500ms") == 0.5
    assert _parse_delay(None) is None
    assert _parse_delay("unknown") is None


def test_rate_limit_delay_prefers_retry_after_header():
    response = httpx.Response(
        429,
        headers={
            "retry-after": "3",
            "x-ratelimit-reset-tokens": "8.5s",
        },
        request=httpx.Request("POST", "https://api.groq.com"),
    )

    assert _rate_limit_delay(response, attempt=0) == 3.0


def test_rate_limit_delay_uses_token_reset_header():
    response = httpx.Response(
        429,
        headers={"x-ratelimit-reset-tokens": "8.5s"},
        request=httpx.Request("POST", "https://api.groq.com"),
    )

    assert _rate_limit_delay(response, attempt=0) == 8.5


def test_rate_limit_delay_uses_bounded_backoff_without_headers():
    response = httpx.Response(
        429,
        request=httpx.Request("POST", "https://api.groq.com"),
    )

    assert _rate_limit_delay(response, attempt=0) == 2.0
    assert _rate_limit_delay(response, attempt=5) == 32.0
