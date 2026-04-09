from datetime import datetime

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    repository_id: str
    prompt: str = Field(min_length=1)
    reference_document_ids: list[str] = Field(default_factory=list)
    reference_file_ids: list[str] = Field(default_factory=list)


class WorkspaceResponse(BaseModel):
    id: str
    repository_id: str
    prompt: str
    status: str
    created_at: datetime


class BlockResponse(BaseModel):
    id: str
    workspace_id: str
    order_index: int
    title: str
    block_type: str
    summary: str
    file_name: str
    content: str


class BlockUpdateRequest(BaseModel):
    content: str


class ChatMessageCreate(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1)
    mentions: list[str] = Field(default_factory=list)


class ChatMessageResponse(BaseModel):
    id: str
    block_id: str
    role: str
    content: str
    mentions: list[str]
    created_at: datetime
