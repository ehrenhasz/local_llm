import json
import sys
from pathlib import Path
from typing import List, Optional, Literal, Union
from pydantic import BaseModel, Field

# Correctly determine the base path for data files (like config.json)
# for both development and PyInstaller bundled mode.
if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the base path is the directory of the executable
    base_path = Path(sys.executable).parent
else:
    # In a normal environment, the base path is the project root
    base_path = Path(__file__).parent.parent

CONFIG_FILE_PATH = base_path / "config.json"

class MinerConfig(BaseModel):
    name: str
    miner_path: str
    wallet: str
    pool: str
    coin: str
    worker: str
    device: Optional[int] = None

class OllamaProviderConfig(BaseModel):
    provider: Literal["ollama"]
    api_base: str = "http://localhost:11434/v1"
    default_model: str = "llama2"

class VertexAIProviderConfig(BaseModel):
    provider: Literal["vertexai"]
    project: str
    location: str
    default_model: str = "gemini-1.0-pro-001"

class BackendConfig(BaseModel):
    miners: List[MinerConfig] = []
    llm: Union[OllamaProviderConfig, VertexAIProviderConfig] = Field(..., discriminator='provider')

def load_config() -> BackendConfig:
    if not CONFIG_FILE_PATH.exists():
        # Create a default config file if it doesn't exist
        print(f"Config file not found. Creating a default one at: {CONFIG_FILE_PATH}")
        default_config_data = {
            "miners": [],
            "llm": {
                "provider": "ollama",
                "api_base": "http://127.0.0.1:8000", # Default to the bundled backend
                "default_model": "llama2"
            }
        }
        with open(CONFIG_FILE_PATH, "w") as f:
            json.dump(default_config_data, f, indent=4)
        return BackendConfig(**default_config_data)
        
    try:
        with open(CONFIG_FILE_PATH, "r") as f:
            data = json.load(f)
            return BackendConfig(**data)
    except (json.JSONDecodeError, TypeError) as e:
        print(f"Warning: Could not decode JSON from {CONFIG_FILE_PATH} or it has incorrect structure. Error: {e}. Using default config.")
        return BackendConfig(llm={"provider": "ollama"}) # Basic default
    except Exception as e:
        print(f"Error loading config from {CONFIG_FILE_PATH}: {e}. Using default config.")
        return BackendConfig(llm={"provider": "ollama"}) # Basic default

def save_config(config: BackendConfig):
    with open(CONFIG_FILE_PATH, "w") as f:
        # Pydantic's model_dump is preferred for serialization
        json.dump(config.model_dump(by_alias=True), f, indent=4)
