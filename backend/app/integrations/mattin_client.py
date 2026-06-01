import json
from typing import Any

import requests
from requests import Response
from requests.exceptions import RequestException

from app.core.config import settings


class MattinClientError(RuntimeError):
    """Raised when a Mattin API request fails."""


class MattinClient:
    def __init__(
        self,
        api_key: str = settings.mattin_api_key,
        app_id: str = settings.mattin_app_id,
        mattin_api_url: str = settings.mattin_api_url,
    ) -> None:
        self.api_key = api_key
        self.app_id = app_id
        self.mattin_api_url = mattin_api_url.rstrip("/")

    def _headers(self, content_type: str | None = "application/json") -> dict[str, str]:
        headers = {
            "accept": "application/json",
            "X-API-KEY": self.api_key,
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _raise_for_status(self, response: Response) -> None:
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = response.text.strip()
            if len(detail) > 500:
                detail = f"{detail[:500]}..."
            raise MattinClientError(
                f"Mattin request failed with status {response.status_code}: {detail or 'No detail'}"
            ) from exc

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        timeout: int = 30,
    ) -> dict[str, Any] | list[Any]:
        url = f"{self.mattin_api_url}{path}"

        is_form_request = data is not None or files is not None
        headers = self._headers(content_type=None if is_form_request else "application/json")

        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_body,
                data=data,
                files=files,
                timeout=timeout,
            )
        except RequestException as exc:
            raise MattinClientError(f"Mattin request error: {exc}") from exc
        self._raise_for_status(response)

        if not response.content:
            return {}

        return response.json()

    # =========================== REPOSITORIES ============================

    def get_all_repositories(self) -> list[dict[str, Any]]:
        payload = self._request_json("GET", f"/app/{self.app_id}/repositories/")
        if isinstance(payload, dict):
            repositories = payload.get("repositories", [])
            if isinstance(repositories, list):
                return repositories
            return []
        return payload

    def create_repository(self, name: str) -> dict[str, Any]:
        payload = self._request_json(
            "POST",
            f"/app/{self.app_id}/repositories/",
            json_body={
                "name": name,
                "embedding_service_id": 1,
                "vector_db_type": "pgvector",
            },
        )
        if isinstance(payload, dict):
            return payload
        raise MattinClientError("Unexpected response shape while creating repository")

    def get_repository(self, repository_id: str) -> dict[str, Any]:
        payload = self._request_json("GET", f"/app/{self.app_id}/repositories/{repository_id}/")
        if isinstance(payload, dict):
            return payload
        raise MattinClientError("Unexpected response shape while fetching repository")

    def update_repository(self, repository_id: str, name: str) -> dict[str, Any]:
        payload = self._request_json(
            "PUT",
            f"/app/{self.app_id}/repositories/{repository_id}/",
            json_body={"name": name},
        )
        if isinstance(payload, dict):
            return payload
        raise MattinClientError("Unexpected response shape while updating repository")

    def delete_repository(self, repository_id: str) -> None:
        self._request_json("DELETE", f"/app/{self.app_id}/repositories/{repository_id}/")

    def get_repository_files(self, repository_id: str, query: str) -> list[dict[str, Any]]:
        payload = self._request_json(
            "GET",
            f"/app/{self.app_id}/repositories/{repository_id}/docs/find",
            params={"query": query},
        )
        if isinstance(payload, dict):
            results = payload.get("results")
            if isinstance(results, list):
                return results
            return []
        return payload

    def upload_repository_file(
        self,
        repository_id: str,
        *,
        file_name: str,
        content_bytes: bytes,
        mime_type: str,
        timeout: int = 60,
    ) -> dict[str, Any]:
        payload = self._request_json(
            "POST",
            f"/app/{self.app_id}/resources/{repository_id}",
            files={"files": (file_name, content_bytes, mime_type)},
            timeout=timeout,
        )
        if isinstance(payload, dict):
            return payload
        raise MattinClientError("Unexpected response shape while uploading repository file")

    def get_repository_resources(self, repository_id: str) -> list[dict[str, Any]]:
        paths = (
            f"/app/{self.app_id}/resources/{repository_id}",
            f"/app/{self.app_id}/repositories/{repository_id}/docs/find",
        )
        last_error: MattinClientError | None = None
        for path in paths:
            try:
                payload = self._request_json("GET", path)
            except MattinClientError as exc:
                last_error = exc
                continue

            if isinstance(payload, list):
                return [item for item in payload if isinstance(item, dict)]

            if isinstance(payload, dict):
                for key in ("resources", "results", "created_resources", "docs", "files"):
                    candidate = payload.get(key)
                    if isinstance(candidate, list):
                        return [item for item in candidate if isinstance(item, dict)]
                return []

        if last_error is not None:
            raise last_error
        return []

    def delete_repository_resource(self, repository_id: str, resource_id: int) -> None:
        self._request_json(
            "DELETE",
            f"/app/{self.app_id}/resources/{repository_id}/{resource_id}",
        )

    # ============================== AGENTS ===============================

    def get_all_agents(self) -> list[dict[str, Any]]:
        payload = self._request_json("GET", f"/app/{self.app_id}/agents/")
        if isinstance(payload, dict):
            agents = payload.get("agents", [])
            if isinstance(agents, list):
                return agents
            return []
        return payload

    def get_agent(self, agent_id: int) -> dict[str, Any]:
        payload = self._request_json("GET", f"/app/{self.app_id}/agents/{agent_id}")
        if isinstance(payload, dict):
            return payload
        raise MattinClientError("Unexpected response shape while fetching agent")

    def create_agent(self, name: str, repository_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": name,
            "description": "",
            "type": "agent",
            "is_tool": False,
            "has_memory": False,
            "memory_max_messages": 20,
            "memory_max_tokens": 4000,
            "memory_summarize_threshold": 4000,
            "system_prompt": "",
            "prompt_template": "",
            "service_id": 0,
            "silo_id": 0,
            "output_parser_id": 0,
            "temperature": 0.7,
            "tool_ids": [],
            "mcp_config_ids": [],
            "skill_ids": [],
        }
        if repository_id:
            payload["repository_id"] = repository_id

        response_payload = self._request_json(
            "POST",
            f"/app/{self.app_id}/agents/",
            json_body=payload,
        )
        if isinstance(response_payload, dict):
            return response_payload
        raise MattinClientError("Unexpected response shape while creating agent")

    def call_agent(
        self,
        agent_id: int,
        message: str,
        *,
        conversation_id: int | None = None,
        file_references: list[int] | None = None,
        files: list[tuple[str, tuple[str, bytes, str]]] | None = None,
        search_params: dict[str, Any] | None = None,
        timeout: int = 45,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {"message": message}
        if conversation_id is not None:
            data["conversation_id"] = str(conversation_id)
        if file_references is not None:
            data["file_references"] = json.dumps(file_references)
        if search_params is not None:
            data["search_params"] = json.dumps(search_params)

        payload = self._request_json(
            "POST",
            f"/app/{self.app_id}/chat/{agent_id}/call",
            data=data,
            files=files or None,
            timeout=timeout,
        )

        if not isinstance(payload, dict):
            raise MattinClientError("Unexpected response shape while calling agent")
        return payload