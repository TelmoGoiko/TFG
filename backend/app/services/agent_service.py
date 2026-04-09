from app.tools.agent_placeholder_tool import AgentPlaceholderTool


class AgentService:
    def __init__(self, tool: AgentPlaceholderTool) -> None:
        self.tool = tool

    def suggest_block_edit(self, user_message: str, selected_snippet: str | None) -> str:
        return self.tool.suggest_edit(
            user_message=user_message,
            selected_snippet=selected_snippet,
        )
