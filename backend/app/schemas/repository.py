from datetime import datetime

from pydantic import BaseModel, Field


class RepositoryCreate(BaseModel):
    owner_id: str
    name: str = Field(min_length=1, max_length=255)
    description: str = ""


class RepositoryResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    description: str
    created_at: datetime


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = ""


class DocumentResponse(BaseModel):
    id: str
    repository_id: str
    title: str
    content: str
    created_at: datetime


class RepositoryFileResponse(BaseModel):
    id: str
    repository_id: str
    file_name: str
    mime_type: str
    size_bytes: int
    created_at: datetime
