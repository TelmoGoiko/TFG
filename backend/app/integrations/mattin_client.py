import requests
from sqlalchemy import false
from app.core.config import settings

class MattinClient:
    def __init__(self, 
                 api_key: str = settings.mattin_api_key, 
                 app_id: str = settings.mattin_app_id, 
                 mattin_api_url: str = settings.mattin_api_url) -> None:
        self.api_key = api_key
        self.app_id = app_id
        self.mattin_api_url = mattin_api_url.rstrip('/')

    #===========================REPOSITORIES======================================

    def get_all_repositories(self) -> list[dict]:
        url = f"{self.mattin_api_url}/app/{self.app_id}/repositories/"
        headers = {
            "accept": "application/json",
            "X-API-KEY": self.api_key,
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    
    def create_repository(self, name: str) -> dict:
        url = f"{self.mattin_api_url}/app/{self.app_id}/repositories/"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key,
        }
        payload = {
            "name": name
        }
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    
    def get_repository(self, repository_id: str) -> dict:
        url = f"{self.mattin_api_url}/app/{self.app_id}/repositories/{repository_id}/"
        headers = {
            "accept": "application/json",
            "X-API-KEY": self.api_key,
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    
    def update_repository(self, repository_id: str, name: str) -> dict:
        url = f"{self.mattin_api_url}/app/{self.app_id}/repositories/{repository_id}/"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key,
        }
        payload = {
            "name": name
        }
        response = requests.put(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    
    def delete_repository(self, repository_id: str) -> None:
        url = f"{self.mattin_api_url}/app/{self.app_id}/repositories/{repository_id}/"
        headers = {
            "accept": "application/json",
            "X-API-KEY": self.api_key,
        }
        response = requests.delete(url, headers=headers, timeout=15)
        response.raise_for_status()

    def get_repository_files(self, repository_id: str, query: str) -> list[dict]:
        url = f"{self.mattin_api_url}/app/{self.app_id}/repositories/{repository_id}/docs/find/"
        headers = {
            "accept": "application/json",
            "X-API-KEY": self.api_key,
        }
        payload = {
            "query": query,
            "metadata": {},
        }
        response = requests.get(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    

    #===========================AGENTS======================================

    def get_all_agents(self) -> list[dict]:
        url = f"{self.mattin_api_url}/app/{self.app_id}/agents/"
        headers = {
            "accept": "application/json",
            "X-API-KEY": self.api_key,
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    
    def create_agent(self, name: str, repository_id: str) -> dict:
        url = f"{self.mattin_api_url}/app/{self.app_id}/agents/"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key,
        }
        payload = {
            "name": name,
            "description": "",
            "type": "agent",
            "is_tool": false,
            "has_memory": false,
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
            "skill_ids": []
        }
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()