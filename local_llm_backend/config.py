import json
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel

CONFIG_FILE_PATH = Path(__file__).parent.parent / "config.json"

class MinerConfig(BaseModel):
    name: str
    miner_path: str
    wallet: str
    pool: str
    coin: str
    worker: str
    device: Optional[int] = None

class BackendConfig(BaseModel):
    miners: List[MinerConfig] = []
    llm_model_path: Optional[str] = None # Path to the local LLM model
    llm_api_base: str = "http://localhost:11434/v1" # Default Ollama API endpoint

def load_config() -> BackendConfig:
    if not CONFIG_FILE_PATH.exists():
        return BackendConfig() # Return default if file doesn't exist
    try:
        with open(CONFIG_FILE_PATH, "r") as f:
            data = json.load(f)
            return BackendConfig(**data)
    except json.JSONDecodeError:
        print(f"Warning: Could not decode JSON from {CONFIG_FILE_PATH}. Using default config.")
        return BackendConfig()
    except Exception as e:
        print(f"Error loading config from {CONFIG_FILE_PATH}: {e}. Using default config.")
        return BackendConfig()

def save_config(config: BackendConfig):
    with open(CONFIG_FILE_PATH, "w") as f:
        json.dump(config.model_dump(), f, indent=4)
