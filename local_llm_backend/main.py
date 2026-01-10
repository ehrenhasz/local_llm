from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
import shlex
import asyncio
import json
import httpx
from pathlib import Path

from local_llm_backend.utils.process_manager import ProcessManager
from local_llm_backend.config import load_config as default_load_config, save_config as default_save_config, BackendConfig, MinerConfig, CONFIG_FILE_PATH
from local_llm_backend.services.system_monitor import get_system_stats as default_get_system_stats
from local_llm_backend.services.ollama_client import OllamaClient
from local_llm_backend.services.recipe_manager import get_recipes as default_get_recipes, read_recipe as default_read_recipe

# --- App Factory for Testability ---
def create_app(
    process_manager_instance: ProcessManager = None,
    ollama_client_instance: OllamaClient = None,
    load_config_fn=default_load_config,
    save_config_fn=default_save_config,
    get_system_stats_fn=default_get_system_stats,
    get_recipes_fn=default_get_recipes,
    read_recipe_fn=default_read_recipe,
):
    app = FastAPI(title="Local LLM Control Backend", version="1.0.0")

    # Store provided instances or create real ones if not provided
    app.state.process_manager = process_manager_instance if process_manager_instance is not None else ProcessManager()
    app.state.ollama_client = ollama_client_instance if ollama_client_instance is not None else OllamaClient()

    @app.on_event("startup")
    async def startup_event():
        # Ensure config.json exists or is created with defaults
        if not CONFIG_FILE_PATH.exists():
            save_config_fn(BackendConfig()) # Use injected save_config
        app.state.config = load_config_fn() # Use injected load_config
        # Now, ensure app.state.ollama_client is configured with the base_url from config.
        # Crucially, we use the *already provided* ollama_client_instance (which is our mock in tests)
        # to update its base_url, rather than creating a new real OllamaClient.
        # If the provided ollama_client_instance is None (production), then it's a real OllamaClient
        # and we update it.
        app.state.ollama_client.base_url = app.state.config.llm_api_base
        app.state.ollama_client.client = httpx.AsyncClient(base_url=app.state.config.llm_api_base) # Update its internal client

    @app.get("/config", response_model=BackendConfig)
    async def get_backend_config():
        return app.state.config

    @app.post("/config", response_model=BackendConfig)
    async def update_backend_config(new_config: BackendConfig):
        save_config_fn(new_config)
        app.state.config = new_config
        app.state.ollama_client.base_url = app.state.config.llm_api_base
        app.state.ollama_client.client = httpx.AsyncClient(base_url=app.state.config.llm_api_base)
        return app.state.config

    @app.get("/")
    async def read_root():
        return {"message": "Local LLM Control Backend is running!"}

    @app.get("/system/stats")
    async def get_system_statistics():
        return get_system_stats_fn()

    @app.post("/llm/start")
    async def start_llm_service():
        try:
            await app.state.ollama_client.get_models()
            return {"status": "Ollama service is reachable", "message": "Assumed Ollama server running."}
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Ollama service not reachable: {e}")

    @app.post("/llm/stop")
    async def stop_llm_service():
        return {"status": "Ollama service stop not directly managed by this backend.", "message": "Please stop Ollama server externally if it was not started by this service."}

    @app.get("/llm/status")
    async def get_llm_status():
        try:
            await app.state.ollama_client.get_models()
            return {"status": "RUNNING", "message": "Ollama service is reachable."}
        except Exception:
            return {"status": "STOPPED", "message": "Ollama service is not reachable."}

    class LLMGenerationRequest(BaseModel):
        model: str
        prompt: str
        stream: bool = False
        max_tokens: int = 100

    @app.post("/llm/generate")
    async def generate_text_with_llm(request: LLMGenerationRequest):
        if not app.state.ollama_client:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Ollama client not initialized.")
        try:
            if request.stream:
                async def stream_generator():
                    async for chunk in app.state.ollama_client.generate(request.model, request.prompt, stream=True, options={"num_predict": request.max_tokens}):
                        yield json.dumps(chunk) + "\n"
                return StreamingResponse(stream_generator(), media_type="application/json")
            else:
                response = await app.state.ollama_client.generate(request.model, request.prompt, stream=False, options={"num_predict": request.max_tokens})
                return response
        except httpx.RequestError as e:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not connect to Ollama service: {e}")
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error during LLM generation: {e}")

    @app.get("/llm/models")
    async def list_ollama_models():
        if not app.state.ollama_client:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Ollama client not initialized.")
        try:
            models = await app.state.ollama_client.get_models()
            return models
        except httpx.RequestError as e:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not connect to Ollama service: {e}")

    class OllamaPullRequest(BaseModel):
        model_name: str

    @app.post("/llm/pull")
    async def pull_ollama_model(request: OllamaPullRequest):
        if not app.state.ollama_client:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Ollama client not initialized.")
        try:
            async def pull_generator():
                async for chunk in app.state.ollama_client.pull_model(request.model_name):
                    yield json.dumps(chunk) + "\n"
            return StreamingResponse(pull_generator(), media_type="application/json")
        except httpx.RequestError as e:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not connect to Ollama service: {e}")
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error pulling Ollama model: {e}")

    @app.get("/recipes")
    async def get_all_recipes():
        return get_recipes_fn()

    @app.get("/recipes/{category}/{name}")
    async def get_single_recipe(category: str, name: str):
        recipe = read_recipe_fn(category, name)
        if not recipe:
            raise HTTPException(status_code=404, detail=f"Recipe '{name}' not found in category '{category}'.")
        return recipe

    @app.post("/miner/start/{miner_name}")
    async def start_miner(miner_name: str):
        config = app.state.config
        miner_config = next((m for m in config.miners if m.name == miner_name), None)
        if not miner_config:
            raise HTTPException(status_code=404, detail=f"Miner '{miner_name}' not found in configuration.")
        command_args = [
            miner_config.miner_path,
            "-a",
            miner_config.coin,
            "-o",
            miner_config.pool,
            "-u",
            miner_config.wallet,
            "-p",
            "x",
            "-w",
            miner_config.worker,
        ]
        if miner_config.device is not None:
            command_args.extend(["-d", str(miner_config.device)])
        final_command = command_args
        if app.state.process_manager.start_process(f"miner_{miner_name}", final_command, cwd=str(Path(miner_config.miner_path).parent)):
            return {"status": f"Miner '{miner_name}' starting", "message": f"Miner process started with PID {app.state.process_manager.processes[f'miner_{miner_name}'].pid}"}
        raise HTTPException(status_code=400, detail=f"Failed to start miner '{miner_name}' or already running.")

    @app.post("/miner/stop/{miner_name}")
    async def stop_miner(miner_name: str):
        if app.state.process_manager.stop_process(f"miner_{miner_name}"):
            return {"status": f"Miner '{miner_name}' stopped"}
        raise HTTPException(status_code=400, detail=f"Failed to stop miner '{miner_name}' or not running.")

    @app.post("/miner/stop_all")
    async def stop_all_miners():
        stopped_miners = []
        for miner_name_key in list(app.state.process_manager.processes.keys()):
            if miner_name_key.startswith("miner_"):
                if app.state.process_manager.stop_process(miner_name_key):
                    stopped_miners.append(miner_name_key.replace("miner_", ""))
        if stopped_miners:
            return {"status": "All configured miners stopped", "stopped_miners": stopped_miners}
        return {"status": "No miners were running or configured to stop."}

    @app.get("/miner/status/{miner_name}")
    async def get_miner_status(miner_name: str):
        status = app.state.process_manager.get_process_status(f"miner_{miner_name}")
        return {"status": status}

    @app.get("/miner/all_status")
    async def get_all_miner_status():
        config = app.state.config
        all_statuses = {}
        for miner in config.miners:
            all_statuses[miner.name] = app.state.process_manager.get_process_status(f"miner_{miner.name}")
        return all_statuses

    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
