import requests
import json
from typing import Dict, Any, Optional

class ApiClient:
    """
    A synchronous client to interact with the FastAPI backend for the GUI.
    """
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url

    def get_system_stats(self) -> Optional[Dict[str, Any]]:
        """Fetches system statistics from the backend."""
        try:
            response = requests.get(f"{self.base_url}/system/stats")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API Error: Could not get system stats: {e}")
            return None

    def start_miner(self, miner_name: str) -> Optional[Dict[str, Any]]:
        """Sends a request to start a specific miner."""
        try:
            response = requests.post(f"{self.base_url}/miner/start/{miner_name}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API Error: Could not start miner {miner_name}: {e}")
            return None

    def stop_miner(self, miner_name: str) -> Optional[Dict[str, Any]]:
        """Sends a request to stop a specific miner."""
        try:
            response = requests.post(f"{self.base_url}/miner/stop/{miner_name}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API Error: Could not stop miner {miner_name}: {e}")
            return None

    def stop_all_miners(self) -> Optional[Dict[str, Any]]:
        """Sends a request to stop all running miners."""
        try:
            response = requests.post(f"{self.base_url}/miner/stop_all")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API Error: Could not stop all miners: {e}")
            return None
            
    def get_all_miner_status(self) -> Dict[str, str]:
        """Fetches the status of all configured miners."""
        try:
            response = requests.get(f"{self.base_url}/miner/all_status")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API Error: Could not get all miner statuses: {e}")
            return {}

    def get_config(self) -> Optional[Dict[str, Any]]:
        """Fetches the current backend configuration."""
        try:
            response = requests.get(f"{self.base_url}/config")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API Error: Could not get config: {e}")
            return None
    
    def update_config(self, config_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Posts an updated configuration to the backend."""
        try:
            response = requests.post(f"{self.base_url}/config", json=config_data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API Error: Could not update config: {e}")
            return None

    def generate_llm(self, model: str, prompt: str, stream: bool = False, max_tokens: int = 100) -> Any:
        """Requests a text generation from the LLM."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "max_tokens": max_tokens
        }
        try:
            # Streaming and non-streaming responses need to be handled differently
            if stream:
                # The caller will need to handle the streaming response
                return requests.post(f"{self.base_url}/llm/generate", json=payload, stream=True)
            else:
                response = requests.post(f"{self.base_url}/llm/generate", json=payload)
                response.raise_for_status()
                return response.json()
        except requests.RequestException as e:
            print(f"API Error: Could not generate LLM text: {e}")
            return None

    def get_llm_models(self) -> Optional[Dict[str, Any]]:
        """Fetches the list of available LLM models."""
        try:
            response = requests.get(f"{self.base_url}/llm/models")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API Error: Could not get LLM models: {e}")
            return None

    def get_recipe(self, category: str, name: str) -> Optional[Dict[str, Any]]:
        """Fetches a single recipe from the backend."""
        try:
            # The backend expects the .txt extension to be stripped
            recipe_name = name.replace('.txt', '')
            response = requests.get(f"{self.base_url}/recipes/{category}/{recipe_name}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API Error: Could not get recipe {category}/{name}: {e}")
            return None
    
    def get_recipes(self) -> Optional[Dict[str, Any]]:
        """Fetches the available recipes."""
        try:
            response = requests.get(f"{self.base_url}/recipes")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API Error: Could not get recipes: {e}")
            return None

# Global client instance for the GUI to use
api_client = ApiClient()
