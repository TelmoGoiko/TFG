from datetime import datetime

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    owner_id: str
    name: str = Field(min_length=1, max_length=255)
    description: str = ""


class WorkspaceRunCreate(BaseModel):
    prompt: str = Field(min_length=1)
    reference_document_ids: list[str] = Field(default_factory=list)
    reference_file_ids: list[str] = Field(default_factory=list)


class WorkspaceResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    description: str
    created_at: datetime


class WorkspaceRunResponse(BaseModel):
    id: str
    workspace_id: str
    prompt: str
    status: str
    created_at: datetime


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = ""


class DocumentResponse(BaseModel):
    id: str
    workspace_id: str
    title: str
    content: str
    created_at: datetime


class WorkspaceFileResponse(BaseModel):
    id: str
    workspace_id: str
    file_name: str
    mime_type: str
    size_bytes: int
    created_at: datetime


class BlockResponse(BaseModel):
    id: str
    workspace_run_id: str
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
