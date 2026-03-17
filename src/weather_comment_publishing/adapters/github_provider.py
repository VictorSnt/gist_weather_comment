from __future__ import annotations

import asyncio
from dataclasses import dataclass

from github import Github
from github.Gist import Gist
from github.GithubException import (
    BadCredentialsException,
    GithubException,
    RateLimitExceededException,
    UnknownObjectException,
)

from src.shared.exceptions import (
    GistAccessDeniedError,
    GistCommentNotAllowedError,
    GistNotFoundError,
    GitHubGistIntegrationError,
)


from src.weather_comment_publishing.protocols import GistPublisherPort


@dataclass(frozen=True, slots=True)
class GitHubGistProvider(GistPublisherPort):
    token: str

    async def publish_comment(self, gist_id: str, content: str) -> int:
        return await asyncio.to_thread(self._publish_comment, gist_id, content)

    def _get_gist(self, gist_id: str) -> Gist:
        try:
            github_client = Github(self.token)
            return github_client.get_gist(id=gist_id)
        
        except UnknownObjectException as exc:
            raise GistNotFoundError("Gist not found.") from exc
        
        except (BadCredentialsException, RateLimitExceededException) as exc:
            raise GitHubGistIntegrationError("Failed to read gist from GitHub.") from exc
        
        except GithubException as exc:
            if getattr(exc, "status", None) == 403:
                raise GistAccessDeniedError("Access denied to gist.") from exc
            raise GitHubGistIntegrationError("Failed to read gist from GitHub.") from exc
        
        except Exception as exc:
            raise GitHubGistIntegrationError("Failed to read gist from GitHub.") from exc

    def _publish_comment(self, gist_id: str, content: str) -> int:
        gist = self._get_gist(gist_id)
        try:
            created_comment = gist.create_comment(body=content)
            comment_id = int(created_comment.id)
            return comment_id
        
        except UnknownObjectException as exc:
            raise GistNotFoundError("Gist not found.") from exc
        
        except (BadCredentialsException, RateLimitExceededException) as exc:
            raise GitHubGistIntegrationError("Failed to publish gist comment on GitHub.") from exc
        
        except GithubException as exc:
            if getattr(exc, "status", None) == 403:
                raise GistCommentNotAllowedError("Not allowed to comment on gist.") from exc
            raise GitHubGistIntegrationError("Failed to publish gist comment on GitHub.") from exc
        except Exception as exc:
            raise GitHubGistIntegrationError("Failed to publish gist comment on GitHub.") from exc
