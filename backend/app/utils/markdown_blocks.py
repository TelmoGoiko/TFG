from app.utils.ids import new_id


def slugify(value: str) -> str:
    return "-".join("".join(ch for ch in value.lower() if ch.isalnum() or ch == " ").split())


def create_file_name(order_index: int, title: str) -> str:
    return f"{order_index + 1:02d}_{slugify(title)}.md"


def build_default_blocks(prompt: str, reference_titles: list[str]) -> list[dict]:
    repository_context = (
        f"Available references: {', '.join(reference_titles)}."
        if reference_titles
        else "No references uploaded yet."
    )

    base = [
        {
            "title": "General index",
            "block_type": "index",
            "summary": "Map of chapters and relationships between blocks.",
            "content": "# Index\n\n- [Context and objectives](./02_context-and-objectives.md)\n- [Offer requirements](./03_offer-requirements.md)\n- [Financial proposal and conditions](./04_financial-proposal-and-conditions.md)\n- [Execution plan](./05_execution-plan.md)\n- [Next steps](./06_next-steps.md)",
        },
        {
            "title": "Context and objectives",
            "block_type": "chapter",
            "summary": "Describe the problem and the intent of the document.",
            "content": f"# Context and objectives\n\nBase request: {prompt.strip()}\n\n{repository_context}",
        },
        {
            "title": "Offer requirements",
            "block_type": "chapter",
            "summary": "Define functional and operational scope.",
            "content": "# Offer requirements\n\n- Scope\n- Deliverables\n- Constraints",
        },
        {
            "title": "Financial proposal and conditions",
            "block_type": "chapter",
            "summary": "Summarize cost and key terms.",
            "content": "# Financial proposal and conditions\n\n- Pricing model\n- Payment terms",
        },
        {
            "title": "Execution plan",
            "block_type": "chapter",
            "summary": "Break down phases and milestones.",
            "content": "# Execution plan\n\n1. Discovery\n2. Development\n3. Validation",
        },
        {
            "title": "Next steps",
            "block_type": "closing",
            "summary": "Actions to approve and kick off the work.",
            "content": "# Next steps\n\n- Internal review\n- Approval\n- Signature",
        },
    ]

    output = []
    for order_index, block in enumerate(base):
        output.append(
            {
                "id": new_id(),
                "order_index": order_index,
                "title": block["title"],
                "block_type": block["block_type"],
                "summary": block["summary"],
                "file_name": create_file_name(order_index, block["title"]),
                "content": block["content"],
            }
        )

    return output
