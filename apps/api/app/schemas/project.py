"""Project API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1)


class Project(BaseModel):
    id: str
    name: str
    created_at: datetime
