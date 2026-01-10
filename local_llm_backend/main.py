from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
import asyncio
import json
import httpx
from pathlib import Path

from local_llm_backend.utils.process_manager import ProcessManager
from local_llm_backend.config import load_config as default_load_config, save_config as default_save_config, BackendConfig, MinerConfig, CONFIG_FILE_PATH
from local_llm_backend.services.system_monitor import get_system_stats as default_get_system_stats
from local_llm_backend.services.llm_clients.base import LLMClient
from local_llm_backend.services.llm_clients import get_llm_client
from local_llm_backend.services.recipe_manager import get_recipes as default_get_recipes, read_recipe as default_read_recipe

# --- App Factory for Testability ---
def create_app(
    process_manager_instance: ProcessManager = None,
    llm_client_instance: LLMClient = None,
    load_config_fn=default_load_config,
    save_config_fn=default_save_config,
    get_system_stats_fn=default_get_system_stats,
    get_recipes_fn=default_get_recipes,
    read_recipe_fn=default_read_recipe,
):
    app = FastAPI(title="Local LLM Control Backend", version="1.0.0")

    app.state.process_manager = process_manager_instance if process_manager_instance is not None else ProcessManager()

    @app.on_event("startup")
    async def startup_event():
        app.state.config = load_config_fn()
        if llm_client_instance:
            app.state.llm_client = llm_client_instance
        else:
            app.state.llm_client = get_llm_client(app.state.config.llm)

    @app.get("/config", response_model=BackendConfig)
    async def get_backend_config():
        return app.state.config

    @app.post("/config", response_model=BackendConfig)
    async def update_backend_config(new_config: BackendConfig):
        save_config_fn(new_config)
        app.state.config = new_config
        app.state.llm_client = get_llm_client(app.state.config.llm)
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
            await app.state.llm_client.get_models()
            return {"status": "LLM service is reachable", "message": f"Provider '{app.state.config.llm.provider}' is active."}
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"LLM service not reachable: {e}")

    @app.post("/llm/stop")
    async def stop_llm_service():
        return {"status": "LLM service stop not directly managed by this backend.", "message": "Please stop the underlying service (e.g., Ollama server) externally."}

    @app.get("/llm/status")
    async def get_llm_status():
        try:
            await app.state.llm_client.get_models()
            return {"status": "RUNNING", "message": f"LLM service '{app.state.config.llm.provider}' is reachable."}
        except Exception:
            return {"status": "STOPPED", "message": f"LLM service '{app.state.config.llm.provider}' is not reachable."}

    class LLMGenerationRequest(BaseModel):
        model: str
        prompt: str
        stream: bool = False
        max_tokens: int = 100

    @app.post("/llm/generate")
    async def generate_text_with_llm(request: LLMGenerationRequest):
        if not app.state.llm_client:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM client not initialized.")
        try:
            if request.stream:
                async def stream_generator():
                    async for chunk in app.state.llm_client.generate(request.model, request.prompt, stream=True, options={"num_predict": request.max_tokens}):
                        yield json.dumps(chunk) + "\n"
                return StreamingResponse(stream_generator(), media_type="application/json")
            else:
                # Aggregate the response from the async generator
                response_chunks = [chunk async for chunk in app.state.llm_client.generate(request.model, request.prompt, stream=False, options={"num_predict": request.max_tokens})]
                # Assuming the non-streamed response is the first (and only) chunk
                return response_chunks[0] if response_chunks else {}
        except httpx.RequestError as e:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not connect to LLM service: {e}")
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error during LLM generation: {e}")

    @app.get("/llm/models")
    async def list_llm_models():
        if not app.state.llm_client:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM client not initialized.")
        try:
            models = await app.state.llm_client.get_models()
            return models
        except httpx.RequestError as e:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not connect to LLM service: {e}")

    class LLMPullRequest(BaseModel):
        model_name: str

    @app.post("/llm/pull")
    async def pull_llm_model(request: LLMPullRequest):
        if not app.state.llm_client:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM client not initialized.")
        try:
            async def pull_generator():
                async for chunk in app.state.llm_client.pull_model(request.model_name):
                    yield json.dumps(chunk) + "\n"
            return StreamingResponse(pull_generator(), media_type="application/json")
        except httpx.RequestError as e:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not connect to LLM service: {e}")
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error pulling LLM model: {e}")

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
