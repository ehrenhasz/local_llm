import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import json
import contextlib
import sys

# Since we are refactoring, we need to ensure the new config models are imported
from local_llm_backend.config import BackendConfig, MinerConfig, OllamaProviderConfig
from local_llm_backend.utils.process_manager import ProcessManager
from local_llm_backend.services.llm_clients.base import LLMClient

# Mock external dependencies
@pytest.fixture(autouse=True)
def mock_dependencies():
    with contextlib.ExitStack() as stack:
        # --- Mock ProcessManager Class and its instance ---
        MockProcessManagerClass = stack.enter_context(patch('local_llm_backend.utils.process_manager.ProcessManager'))
        mock_process_manager_instance = MockProcessManagerClass.return_value 
        
        mock_process_manager_instance.processes = {}
        def mock_start_process(name, command, cwd=None):
            if name not in mock_process_manager_instance.processes or mock_process_manager_instance.processes[name].poll() is not None:
                mock_process_manager_instance.processes[name] = MagicMock(pid=12345, name=name, poll=lambda: None)
                return True
            return False
        mock_process_manager_instance.start_process.side_effect = mock_start_process

        def mock_stop_process(name):
            if name in mock_process_manager_instance.processes:
                del mock_process_manager_instance.processes[name]
                return True
            return False
        mock_process_manager_instance.stop_process.side_effect = mock_stop_process

        mock_process_manager_instance.get_process_status.side_effect = \
            lambda name: "RUNNING" if name in mock_process_manager_instance.processes and \
                                      mock_process_manager_instance.processes[name].poll() is None else "STOPPED"

        # --- Mock a generic LLMClient instance ---
        mock_llm_client_instance = MagicMock(spec=LLMClient)

        async def mock_generate_stream_fn(*args, **kwargs):
            yield {"choices": [{"delta": {"content": "mocked llm response"}}]}
        
        # Make the mock's generate method an async generator
        mock_llm_client_instance.generate = MagicMock(return_value=mock_generate_stream_fn())

        mock_llm_client_instance.get_models = AsyncMock(return_value={"models": [{"name": "llama2"}, {"name": "mistral"}]})
        
        async def mock_pull_model_generator_fn(*args, **kwargs):
            yield {"status": "pulling"}
        
        mock_llm_client_instance.pull_model = MagicMock(return_value=mock_pull_model_generator_fn())

        # --- Mock Functions to be injected into create_app() ---
        mock_get_system_stats = MagicMock(return_value={"cpu": {"percent": 10}, "ram": {"percent": 20}, "gpus": []})
        mock_load_config = MagicMock()
        mock_save_config = MagicMock()

        # Update mock_config to use the new discriminated union structure
        mock_config = BackendConfig(
            miners=[
                MinerConfig(name="test_miner", miner_path="/path/to/miner", wallet="wallet_addr", pool="pool.com:1234", coin="ETH", worker="worker1"),
            ],
            llm=OllamaProviderConfig(provider="ollama", api_base="http://mock-ollama:11434/v1", default_model="llama2")
        )
        mock_load_config.return_value = mock_config

        mock_get_recipes = MagicMock(return_value={"category1": ["recipe1", "recipe2"]})
        mock_read_recipe = MagicMock(return_value={"description": "Mock recipe", "prompt": "Mock prompt content"})

        yield {
            "mock_process_manager_instance": mock_process_manager_instance,
            "mock_llm_client_instance": mock_llm_client_instance,
            "mock_get_system_stats": mock_get_system_stats,
            "mock_load_config": mock_load_config,
            "mock_save_config": mock_save_config,
            "mock_get_recipes": mock_get_recipes,
            "mock_read_recipe": mock_read_recipe,
        }

@pytest.fixture
def client(mock_dependencies):
    # Clear module cache for all relevant modules to ensure fresh import with patches active
    modules_to_delete = [
        'local_llm_backend.main',
        'local_llm_backend.utils.process_manager',
        'local_llm_backend.services.llm_clients.base',
        'local_llm_backend.services.llm_clients.ollama',
        'local_llm_backend.services.llm_clients.vertexai',
        'local_llm_backend.services.llm_clients.factory',
        'local_llm_backend.services.llm_clients',
        'local_llm_backend.config',
        'local_llm_backend.services.system_monitor',
        'local_llm_backend.services.recipe_manager',
    ]
    for module_name in modules_to_delete:
        if module_name in sys.modules:
            del sys.modules[module_name]

    from local_llm_backend.main import create_app
    
    app = create_app(
        process_manager_instance=mock_dependencies["mock_process_manager_instance"],
        llm_client_instance=mock_dependencies["mock_llm_client_instance"],
        load_config_fn=mock_dependencies["mock_load_config"],
        save_config_fn=mock_dependencies["mock_save_config"],
        get_system_stats_fn=mock_dependencies["mock_get_system_stats"],
        get_recipes_fn=mock_dependencies["mock_get_recipes"],
        read_recipe_fn=mock_dependencies["mock_read_recipe"],
    )
    
    with TestClient(app) as test_client:
        yield test_client

def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Local LLM Control Backend is running!"}

def test_get_backend_config(client, mock_dependencies):
    response = client.get("/config")
    assert response.status_code == 200
    assert response.json()["miners"][0]["name"] == "test_miner"
    assert response.json()["llm"]["provider"] == "ollama"
    mock_dependencies["mock_load_config"].assert_called_once()

def test_update_backend_config(client, mock_dependencies):
    updated_config_data = {
        "miners": [],
        "llm": {
            "provider": "vertexai",
            "project": "new-project",
            "location": "us-central1",
            "default_model": "gemini-1.5-pro"
        }
    }
    response = client.post("/config", json=updated_config_data)
    assert response.status_code == 200
    assert response.json()["llm"]["project"] == "new-project"
    
    mock_dependencies["mock_save_config"].assert_called_once()
    saved_config = mock_dependencies["mock_save_config"].call_args[0][0]
    assert saved_config.llm.provider == "vertexai"

def test_get_system_statistics(client, mock_dependencies):
    response = client.get("/system/stats")
    assert response.status_code == 200
    assert "cpu" in response.json()
    assert response.json()["cpu"]["percent"] == 10
    mock_dependencies["mock_get_system_stats"].assert_called_once()

def test_start_llm_service_success(client, mock_dependencies):
    response = client.post("/llm/start")
    assert response.status_code == 200
    assert "LLM service is reachable" in response.json()["status"]
    assert "Provider 'ollama' is active" in response.json()["message"]
    mock_dependencies["mock_llm_client_instance"].get_models.assert_called_once()

def test_start_llm_service_failure(client, mock_dependencies):
    mock_dependencies["mock_llm_client_instance"].get_models.side_effect = Exception("LLM not found")
    response = client.post("/llm/start")
    assert response.status_code == 503
    assert "LLM service not reachable" in response.json()["detail"]

def test_get_llm_status_running(client, mock_dependencies):
    response = client.get("/llm/status")
    assert response.status_code == 200
    assert response.json()["status"] == "RUNNING"
    assert "LLM service 'ollama' is reachable" in response.json()["message"]

def test_generate_text_with_llm_success_non_stream(client, mock_dependencies):
    response = client.post("/llm/generate", json={
        "model": "llama2", "prompt": "hello world", "stream": False, "max_tokens": 50
    })
    assert response.status_code == 200
    assert response.json() == {"choices": [{"delta": {"content": "mocked llm response"}}]}
    mock_dependencies["mock_llm_client_instance"].generate.assert_called_once_with(
        "llama2", "hello world", stream=False, options={'num_predict': 50}
    )

def test_list_llm_models_success(client, mock_dependencies):
    response = client.get("/llm/models")
    assert response.status_code == 200
    assert response.json() == {"models": [{"name": "llama2"}, {"name": "mistral"}]}
    mock_dependencies["mock_llm_client_instance"].get_models.assert_called_once()

def test_pull_llm_model_success(client, mock_dependencies):
    response = client.post("/llm/pull", json={"model_name": "llama2"})
    assert response.status_code == 200
    # For streaming responses, check the content line-by-line
    assert json.loads(response.text.strip()) == {"status": "pulling"}
    mock_dependencies["mock_llm_client_instance"].pull_model.assert_called_once_with("llama2")

# --- Miner tests remain largely the same, so they are kept as is ---
def test_start_miner_success(client, mock_dependencies):
    response = client.post("/miner/start/test_miner")
    assert response.status_code == 200
    assert "Miner 'test_miner' starting" in response.json()["status"]
    mock_dependencies["mock_process_manager_instance"].start_process.assert_called_once()

def test_stop_miner_success(client, mock_dependencies):
    mock_dependencies["mock_process_manager_instance"].processes["miner_test_miner"] = MagicMock(pid=12345, poll=lambda: None)
    response = client.post("/miner/stop/test_miner")
    assert response.status_code == 200
    assert "Miner 'test_miner' stopped" in response.json()["status"]
    mock_dependencies["mock_process_manager_instance"].stop_process.assert_called_once_with("miner_test_miner")

# (Keep other miner and recipe tests as they are not affected by the LLM client refactoring)
def test_get_all_recipes(client, mock_dependencies):
    response = client.get("/recipes")
    assert response.status_code == 200
    assert response.json() == {"category1": ["recipe1", "recipe2"]}
    mock_dependencies["mock_get_recipes"].assert_called_once()

def test_get_single_recipe_success(client, mock_dependencies):
    response = client.get("/recipes/category1/recipe1")
    assert response.status_code == 200
    assert response.json() == {"description": "Mock recipe", "prompt": "Mock prompt content"}
    mock_dependencies["mock_read_recipe"].assert_called_once_with("category1", "recipe1")