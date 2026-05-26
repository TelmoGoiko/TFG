from datetime import datetime

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    owner_id: str
    name: str = Field(min_length=1, max_length=255)
    description: str = ""


class WorkspaceRunCreate(BaseModel):
    prompt: str = Field(min_length=1)
    reference_file_ids: list[str] = Field(default_factory=list)


class WorkspaceResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    description: str
    mattin_repository_id: str | None = None
    created_at: datetime


class WorkspaceRunResponse(BaseModel):
    id: str
    workspace_id: str
    prompt: str
    status: str
    created_at: datetime


class WorkspaceFileResponse(BaseModel):
    id: str
    workspace_id: str
    file_name: str
    mime_type: str
    size_bytes: int
    mattin_file_id: int | None = None
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
    meta: str = "{}"


class BlockUpdateRequest(BaseModel):
    content: str


class BlockCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    summary: str = ""
    content: str = ""
    block_type: str = "chapter"
    file_name: str | None = None
    order_index: int | None = None
    insert_before_block_id: str | None = None
    insert_after_block_id: str | None = None


class BlockRelationshipCreate(BaseModel):
    target_block_id: str = Field(min_length=1)
    relationship_type: str = Field(min_length=1, max_length=50)
    description: str = ""


class BlockRelationshipResponse(BaseModel):
    id: str
    source_block_id: str
    target_block_id: str
    relationship_type: str
    description: str
    auto_created: bool
    created_at: datetime


class ImpactSuggestion(BaseModel):
    id: str
    source_block_id: str
    affected_block_id: str
    affected_block_title: str
    suggestion: str
    reason: str
    relationship_type: str
    status: str = "pending"
    conversation_id: int | None = None
    created_at: datetime | None = None


class ImpactSuggestionApplyRequest(BaseModel):
    suggestion: str = Field(min_length=1)
    suggestion_id: str | None = None


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


class BlockAgentChatRequest(BaseModel):
    user_message: str = Field(min_length=1)
    selected_snippet: str | None = None
    conversation_id: int | None = None
    chat_agent_id: int | None = None


class BlockAgentChatResponse(BaseModel):
    assistant_message: str
    conversation_id: int | None = None
    applied: bool
    proposed_content: str | None = None
    updated_content: str | None = None
    impact_suggestions: list[ImpactSuggestion] = Field(default_factory=list)
