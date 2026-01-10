# Local LLM Control Backend

This FastAPI application serves as the OS-agnostic control backend for managing local Large Language Models (LLMs) via Ollama and cryptocurrency miners. It provides a RESTful API to start/stop services, monitor system statistics, and interact with LLMs.

## Features

*   **OS-Agnostic:** Built with Python and FastAPI, ensuring compatibility across Windows, Linux, and macOS.
*   **LLM Control:** Integrate with Ollama for local LLM management, including text generation, model listing, and pulling.
*   **Crypto Miner Control:** Start and stop various cryptocurrency miners based on configuration.
*   **System Monitoring:** Real-time statistics for CPU, RAM, and GPU usage.
*   **Configuration Management:** Dynamic configuration via API for miners and LLM settings.
*   **Recipe Management:** Store and retrieve LLM prompts ("recipes") for common tasks.

## Setup

1.  **Navigate to the Backend Directory:**
    ```bash
    cd local_llm/local_llm_backend
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Install Ollama (if not already installed):**
    This backend integrates with Ollama. Download and install Ollama from [ollama.ai](https://ollama.ai/). Ensure the Ollama server is running (e.g., by running `ollama serve` in your terminal or as a system service).

## Configuration

The backend uses a `config.json` file in the `local_llm` directory. If it doesn't exist, a default will be created on startup. You can manage this configuration via the `/config` API endpoints.

Example `config.json`:
```json
{
    "miners": [
        {
            "name": "my_eth_miner",
            "miner_path": "/path/to/t-rex.exe",
            "wallet": "YOUR_ETH_WALLET_ADDRESS",
            "pool": "stratum+tcp://eth.pool.com:4444",
            "coin": "ETH",
            "worker": "myworker",
            "device": 0
        }
    ],
    "llm_model_path": "llama2",
    "llm_api_base": "http://localhost:11434/v1"
}
```

*   `miners`: A list of miner configurations.
    *   `name`: Unique name for the miner.
    *   `miner_path`: Absolute path to the miner executable.
    *   `wallet`: Your cryptocurrency wallet address.
    *   `pool`: Mining pool address.
    *   `coin`: Cryptocurrency to mine (e.g., "ETH").
    *   `worker`: Worker name.
    *   `device`: (Optional) GPU device index.
*   `llm_model_path`: The default LLM model to use for generation (must be available in Ollama).
*   `llm_api_base`: The base URL for your Ollama API (default: `http://localhost:11434/v1`).

## Running the Application

To start the FastAPI server:

```bash
python main.py
# Or using uvicorn directly:
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API documentation (Swagger UI) will be available at `http://localhost:8000/docs`.

## API Endpoints

### Root

*   **GET `/`**: Check if the backend is running.
    *   `Response`: `{"message": "Local LLM Control Backend is running!"}`

### Configuration

*   **GET `/config`**: Retrieve the current backend configuration.
    *   `Response`: `BackendConfig` object.
*   **POST `/config`**: Update the backend configuration.
    *   `Request Body`: `BackendConfig` object.
    *   `Response`: Updated `BackendConfig` object.

### System Monitoring

*   **GET `/system/stats`**: Get current CPU, RAM, and GPU usage statistics.
    *   `Response`: JSON object with system statistics.

### LLM Control

*   **POST `/llm/start`**: Check if the Ollama service is reachable.
    *   `Response`: `{"status": "Ollama service is reachable", ...}` or error.
*   **POST `/llm/stop`**: Placeholder - Ollama server stop is not directly managed.
*   **GET `/llm/status`**: Get the reachability status of the Ollama service.
*   **POST `/llm/generate`**: Generate text using the configured LLM.
    *   `Request Body`: `{"model": "model_name", "prompt": "your prompt", "stream": false, "max_tokens": 100}`
    *   `Response`: JSON object with LLM response (can be streaming).
*   **GET `/llm/models`**: List available Ollama models.
*   **POST `/llm/pull`**: Pull an Ollama model.
    *   `Request Body`: `{"model_name": "model_to_pull"}`
    *   `Response`: Streaming JSON object with pull status.

### Crypto Miner Control

*   **POST `/miner/start/{miner_name}`**: Start a specific miner.
*   **POST `/miner/stop/{miner_name}`**: Stop a specific miner.
*   **POST `/miner/stop_all`**: Stop all running miners.
*   **GET `/miner/status/{miner_name}`**: Get the status of a specific miner.
*   **GET `/miner/all_status`**: Get the status of all configured miners.

### Recipe Management

*   **GET `/recipes`**: List all available LLM recipes by category.
*   **GET `/recipes/{category}/{name}`**: Get the content of a specific LLM recipe.

## Running Tests

To run the unit tests:

```bash
cd local_llm/local_llm_backend
pytest tests/
```

## Example Usage (using `curl`)

### Get System Stats

```bash
curl http://localhost:8000/system/stats
```

### Update Configuration

```bash
curl -X POST http://localhost:8000/config -H "Content-Type: application/json" -d 
    "{
    \"miners\": [
        {
            \"name\": \"my_test_miner\",
            \"miner_path\": \"C:\\miners\\t-rex.exe\",
            \"wallet\": \"0xYourEthereumWalletAddressHere\",
            \"pool\": \"stratum+tcp://eu.ethermine.org:4444\",
            \"coin\": \"ETH\",
            \"worker\": \"myRig\",
            \"device\": 0
        }
    ],
    \"llm_model_path\": \"llama2\",
    \"llm_api_base\": \"http://localhost:11434/v1\"
}"
```

### Start an LLM Generation

```bash
curl -X POST http://localhost:8000/llm/generate -H "Content-Type: application/json" -d 
    "{
    \"model\": \"llama2\",
    \"prompt\": \"Write a short poem about AI.\",
    \"stream\": false,
    \"max_tokens\": 100
}"
```

### Start a Miner

```bash
curl -X POST http://localhost:8000/miner/start/my_test_miner
```

### Stop a Miner

```bash
curl -X POST http://localhost:8000/miner/stop/my_test_miner
```
