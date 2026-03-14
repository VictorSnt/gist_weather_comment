from __future__ import annotations

from pydantic import BaseModel


class GistCommentPayload(BaseModel):
    id: int
