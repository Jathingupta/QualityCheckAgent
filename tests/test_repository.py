import pytest
from app.repository import validate_github_url


def test_accepts_github_url():
    clone_url, name = validate_github_url("https://github.com/octocat/Hello-World")
    assert clone_url == "https://github.com/octocat/Hello-World.git"
    assert name == "octocat/Hello-World"


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/a/b",
        "https://example.com/a/b",
        "https://github.com/",
        "file:///tmp/x",
    ],
)
def test_rejects_unsupported_urls(url):
    with pytest.raises(ValueError):
        validate_github_url(url)
