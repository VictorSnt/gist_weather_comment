from __future__ import annotations

import pytest
from github.GithubException import (
    BadCredentialsException,
    GithubException,
    RateLimitExceededException,
    UnknownObjectException,
)

from src.weather_comment_publishing.adapters.github_provider import GitHubGistProvider
from src.shared.exceptions import (
    GistAccessDeniedError,
    GistCommentNotAllowedError,
    GistNotFoundError,
    GitHubGistIntegrationError,
)


class FakeComment:
    def __init__(self, comment_id: int) -> None:
        self.id = comment_id


class FakeGist:
    def __init__(
        self,
        *,
        create_comment_error: Exception | None = None,
        comment_id: int = 123,
    ) -> None:
        self.create_comment_error = create_comment_error
        self.comment_id = comment_id

    def create_comment(self, body: str) -> FakeComment:
        if self.create_comment_error is not None:
            raise self.create_comment_error
        return FakeComment(self.comment_id)


class FakeGithub:
    def __init__(
        self,
        *,
        gist: FakeGist | None = None,
        get_error: Exception | None = None,
    ) -> None:
        self.gist = gist
        self.get_error = get_error

    def get_gist(self, id: str) -> FakeGist:
        if self.get_error is not None:
            raise self.get_error
        assert self.gist is not None
        return self.gist


def _patch_github(monkeypatch: pytest.MonkeyPatch, fake_github: FakeGithub) -> None:
    monkeypatch.setattr(
        "src.weather_comment_publishing.adapters.github_provider.Github",
        lambda token: fake_github,
    )


def _client() -> GitHubGistProvider:
    return GitHubGistProvider(token="token")


@pytest.mark.asyncio
async def test_publish_comment_returns_comment_id(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeGithub(gist=FakeGist(comment_id=456))
    _patch_github(monkeypatch, fake)

    comment_id = await _client().publish_comment(gist_id="abc123", content="hello")

    assert comment_id == 456


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("get_error", "expected_exception", "expected_message"),
    [
        (
            UnknownObjectException(404, "not found", None),
            GistNotFoundError,
            "Gist not found",
        ),
        (
            BadCredentialsException(401, "bad credentials", None),
            GitHubGistIntegrationError,
            "Failed to read gist",
        ),
        (
            RateLimitExceededException(403, "rate limit", None),
            GitHubGistIntegrationError,
            "Failed to read gist",
        ),
        (
            GithubException(403, "forbidden", None),
            GistAccessDeniedError,
            "Access denied",
        ),
    ],
)
async def test_publish_comment_maps_get_gist_errors(
    monkeypatch: pytest.MonkeyPatch,
    get_error: Exception,
    expected_exception: type[Exception],
    expected_message: str,
) -> None:
    fake = FakeGithub(get_error=get_error)
    _patch_github(monkeypatch, fake)

    with pytest.raises(expected_exception, match=expected_message):
        await _client().publish_comment(gist_id="abc123", content="hello")


@pytest.mark.asyncio
async def test_publish_comment_raises_comment_not_allowed_on_forbidden_comment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeGithub(
        gist=FakeGist(
            create_comment_error=GithubException(403, "forbidden", None)
        )
    )
    _patch_github(monkeypatch, fake)

    with pytest.raises(GistCommentNotAllowedError, match="Not allowed to comment"):
        await _client().publish_comment(gist_id="abc123", content="hello")


@pytest.mark.asyncio
async def test_publish_comment_raises_integration_error_on_unexpected_comment_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeGithub(gist=FakeGist(create_comment_error=RuntimeError("boom")))
    _patch_github(monkeypatch, fake)

    with pytest.raises(
        GitHubGistIntegrationError,
        match="Failed to publish gist comment",
    ):
        await _client().publish_comment(gist_id="abc123", content="hello")