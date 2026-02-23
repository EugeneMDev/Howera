"""Authentication schemas."""

from pydantic import BaseModel, Field


class AuthPrincipal(BaseModel):
    """Normalized authenticated principal used by business services."""

    user_id: str = Field(min_length=1)
    role: str = Field(default="editor", min_length=1)
