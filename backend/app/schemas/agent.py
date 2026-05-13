from pydantic import BaseModel, Field


class AgentSuggestRequest(BaseModel):
    user_message: str = Field(min_length=1)
    selected_snippet: str | None = None


class AgentSuggestResponse(BaseModel):
    assistant_message: str
