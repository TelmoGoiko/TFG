class AgentPlaceholderTool:
    """Placeholder tool for future LLM/agent integration."""

    def suggest_edit(self, user_message: str, selected_snippet: str | None) -> str:
        snippet_hint = (
            f"\n\nMentioned snippet: \"{selected_snippet}\"."
            if selected_snippet
            else ""
        )
        return (
            f"Improvement proposal based on: \"{user_message}\"."
            "\n\nSuggestion: add concrete metrics, dates, and acceptance criteria."
            f"{snippet_hint}"
        )
