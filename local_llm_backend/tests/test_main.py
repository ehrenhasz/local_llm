import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import json
import contextlib
import sys

from local_llm_backend.config import BackendConfig, MinerConfig
from local_llm_backend.utils.process_manager import ProcessManager
from local_llm_backend.services.ollama_client import OllamaClient

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

        mock_process_manager_instance.get_process_status.side_effect = 
            lambda name: "RUNNING" if name in mock_process_manager_instance.processes and 
                                      mock_process_manager_instance.processes[name].poll() is None else "STOPPED"


        # --- Mock OllamaClient Class and its instance ---
        MockOllamaClientClass = stack.enter_context(patch('local_llm_backend.services.ollama_client.OllamaClient'))
        mock_ollama_client_instance = MockOllamaClientClass.return_value

        async def mock_generate_stream_fn(*args, **kwargs):
            yield {"choices": [{"delta": {"content": "mocked llm response"}}]}
        mock_ollama_client_instance.generate.side_effect = mock_generate_stream_fn
        mock_ollama_client_instance.generate.return_value.__aiter__.return_value = mock_generate_stream_fn()

        mock_ollama_client_instance.get_models.side_effect = 
            lambda: AsyncMock(return_value={"models": [{"name": "llama2"}, {"name": "mistral"}]})()
        
        async def mock_pull_model_generator_fn(*args, **kwargs):
            yield {"status": "pulling"}
        mock_ollama_client_instance.pull_model.side_effect = mock_pull_model_generator_fn
        mock_ollama_client_instance.pull_model.return_value.__aiter__.return_value = mock_pull_model_generator_fn()


        # --- Mock Functions to be injected into create_app() ---
        mock_get_system_stats = MagicMock(return_value={"cpu": {"percent": 10}, "ram": {"percent": 20}, "gpus": []})
        mock_load_config = MagicMock()
        mock_save_config = MagicMock()

        mock_config = BackendConfig(
            miners=[
                MinerConfig(name="test_miner", miner_path="/path/to/miner", wallet="wallet_addr", pool="pool.com:1234", coin="ETH", worker="worker1"),
            ],
            llm_model_path="llama2",
            llm_api_base="http://mock-ollama:11434/v1"
        )
        mock_load_config.return_value = mock_config

        mock_get_recipes = MagicMock(return_value={"category1": ["recipe1", "recipe2"]})
        mock_read_recipe = MagicMock(return_value={"description": "Mock recipe", "prompt": "Mock prompt content"})

        yield { # Yield a dictionary of mocks to be accessed by tests
            "mock_process_manager_instance": mock_process_manager_instance,
            "mock_ollama_client_instance": mock_ollama_client_instance,
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
        'local_llm_backend.services.ollama_client',
        'local_llm_backend.config',
        'local_llm_backend.services.system_monitor',
        'local_llm_backend.services.recipe_manager',
    ]
    for module_name in modules_to_delete:
        if module_name in sys.modules:
            del sys.modules[module_name]

    from local_llm_backend.main import create_app
    
    # Create app, injecting mocked instances and functions
    app = create_app(
        process_manager_instance=mock_dependencies["mock_process_manager_instance"],
        ollama_client_instance=mock_dependencies["mock_ollama_client_instance"],
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
    mock_dependencies["mock_load_config"].assert_called_once()

def test_update_backend_config(client, mock_dependencies):
    updated_config_data = {
        "miners": [],
        "llm_model_path": "codellama",
        "llm_api_base": "http://new-ollama:11434/v1"
    }
    response = client.post("/config", json=updated_config_data)
    assert response.status_code == 200
    assert response.json()["llm_model_path"] == "codellama"
    
    # Verify save_config was called with the updated config
    mock_dependencies["mock_save_config"].assert_called_once()
    saved_config = mock_dependencies["mock_save_config"].call_args[0][0]
    assert saved_config.llm_model_path == "codellama"

def test_get_system_statistics(client, mock_dependencies):
    response = client.get("/system/stats")
    assert response.status_code == 200
    assert "cpu" in response.json()
    assert response.json()["cpu"]["percent"] == 10
    mock_dependencies["mock_get_system_stats"].assert_called_once()

def test_start_llm_service_success(client, mock_dependencies):
    response = client.post("/llm/start")
    assert response.status_code == 200
    assert response.json() == {"status": "Ollama service is reachable", "message": "Assumed Ollama server running."}
    mock_dependencies["mock_ollama_client_instance"].get_models.assert_called_once()

def test_start_llm_service_failure_no_ollama(client, mock_dependencies):
    mock_dependencies["mock_ollama_client_instance"].get_models.side_effect = Exception("Ollama not found") # Simulate Ollama not reachable
    response = client.post("/llm/start")
    assert response.status_code == 503
    assert "Ollama service not reachable" in response.json()["detail"]
    mock_dependencies["mock_ollama_client_instance"].get_models.assert_called_once()

def test_stop_llm_service(client, mock_dependencies):
    response = client.post("/llm/stop")
    assert response.status_code == 200
    assert response.json() == {"status": "Ollama service stop not directly managed by this backend.", "message": "Please stop Ollama server externally if it was not started by this service."}

def test_get_llm_status_running(client, mock_dependencies):
    response = client.get("/llm/status")
    assert response.status_code == 200
    assert response.json() == {"status": "RUNNING", "message": "Ollama service is reachable."}
    mock_dependencies["mock_ollama_client_instance"].get_models.assert_called_once()

def test_get_llm_status_stopped(client, mock_dependencies):
    mock_dependencies["mock_ollama_client_instance"].get_models.side_effect = Exception("Connection refused") # Simulate Ollama not reachable
    response = client.get("/llm/status")
    assert response.status_code == 200
    assert response.json() == {"status": "STOPPED", "message": "Ollama service is not reachable."}
    mock_dependencies["mock_ollama_client_instance"].get_models.assert_called_once()

def test_generate_text_with_llm_success(client, mock_dependencies):
    response = client.post("/llm/generate", json= {
        "model": "llama2",
        "prompt": "hello world",
        "stream": False,
        "max_tokens": 50
    })
    assert response.status_code == 200
    assert response.json() == {"choices": [{"delta": {"content": "mocked llm response"}}] } 
    mock_dependencies["mock_ollama_client_instance"].generate.assert_called_once_with(
        "llama2", "hello world", stream=False, options={'num_predict': 50}
    )

def test_list_ollama_models_success(client, mock_dependencies):
    response = client.get("/llm/models")
    assert response.status_code == 200
    assert response.json() == {"models": [{"name": "llama2"}, {"name": "mistral"}]}
    mock_dependencies["mock_ollama_client_instance"].get_models.assert_called_once()

def test_pull_ollama_model_success(client, mock_dependencies):
    response = client.post("/llm/pull", json= {
        "model_name": "llama2"
    })
    assert response.status_code == 200
    assert response.text == json.dumps({"status": "pulling"}) + "\n"
    mock_dependencies["mock_ollama_client_instance"].pull_model.assert_called_once_with("llama2")

def test_start_miner_success(client, mock_dependencies):
    response = client.post("/miner/start/test_miner")
    assert response.status_code == 200
    assert "Miner 'test_miner' starting" in response.json()["status"]
    mock_dependencies["mock_process_manager_instance"].start_process.assert_called_once_with(
        "miner_test_miner",
        ['/path/to/miner', '-a', 'ETH', '-o', 'pool.com:1234', '-u', 'wallet_addr', '-p', 'x', '-w', 'worker1'],
        cwd=str(Path('/path/to/miner').parent)
    )

def test_start_miner_not_found(client, mock_dependencies):
    response = client.post("/miner/start/non_existent_miner")
    assert response.status_code == 404
    assert "Miner 'non_existent_miner' not found" in response.json()["detail"]

def test_stop_miner_success(client, mock_dependencies):
    # Need to start the miner first for stop to make sense and for process_manager.processes to be populated
    # The mock_start_process side_effect in the fixture ensures this for the mock_process_manager_instance
    # so we just need to ensure the process exists in its internal dict before stopping
    mock_dependencies["mock_process_manager_instance"].processes["miner_test_miner"] = MagicMock(pid=12345, poll=lambda: None)
    response = client.post("/miner/stop/test_miner")
    assert response.status_code == 200
    assert "Miner 'test_miner' stopped" in response.json()["status"]
    mock_dependencies["mock_process_manager_instance"].stop_process.assert_called_once_with("miner_test_miner")

def test_stop_all_miners_success(client, mock_dependencies):
    # Simulate a running miner by populating the mock process_manager_instance.processes
    mock_dependencies["mock_process_manager_instance"].processes = {"miner_test_miner": MagicMock(pid=123, poll=lambda: None)}
    response = client.post("/miner/stop_all")
    assert response.status_code == 200
    assert response.json()["status"] == "All configured miners stopped"
    assert "test_miner" in response.json()["stopped_miners"]
    mock_dependencies["mock_process_manager_instance"].stop_process.assert_called_once_with("miner_test_miner")

def test_get_miner_status(client, mock_dependencies):
    # Simulate a running miner so that get_process_status returns RUNNING
    mock_dependencies["mock_process_manager_instance"].processes["miner_test_miner"] = MagicMock(pid=12345, poll=lambda: None)
    response = client.get("/miner/status/test_miner")
    assert response.status_code == 200
    assert response.json()["status"] == "RUNNING"
    mock_dependencies["mock_process_manager_instance"].get_process_status.assert_called_once_with("miner_test_miner")

def test_get_all_miner_status(client, mock_dependencies):
    # Simulate a running miner so that get_process_status returns RUNNING
    mock_dependencies["mock_process_manager_instance"].processes["miner_test_miner"] = MagicMock(pid=12345, poll=lambda: None)
    response = client.get("/miner/all_status")
    assert response.status_code == 200
    assert response.json() == {"test_miner": "RUNNING"}
    # get_process_status will be called for each miner in config.miners. Here it's only one.
    mock_dependencies["mock_process_manager_instance"].get_process_status.assert_called_once_with("miner_test_miner")

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

def test_get_single_recipe_not_found(client, mock_dependencies):
    mock_dependencies["mock_read_recipe"].return_value = None # Override for this specific test
    response = client.get("/recipes/category1/non_existent_recipe")
    assert response.status_code == 404
    assert "Recipe 'non_existent_recipe' not found" in response.json()["detail"]
    mock_dependencies["mock_read_recipe"].assert_called_once_with("category1", "non_existent_recipe")