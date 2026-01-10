import httpx
from typing import Dict, Any, AsyncGenerator
import asyncio
import json

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434/v1"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=self.base_url)

    async def generate(self, model: str, prompt: str, stream: bool = False, **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        url = "/chat/completions"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream,
            **kwargs
        }

        if stream:
            async with self.client.stream("POST", url, headers=headers, json=payload, timeout=None) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    decoded_chunk = chunk.decode("utf-8")
                    # Ollama sends SSE with 'data: {...}' and a final '[DONE]' message
                    for line in decoded_chunk.splitlines():
                        if line.startswith("data: "):
                            try:
                                json_data = json.loads(line[len("data: "):])
                                if "content" in json_data["choices"][0]["delta"]:
                                    yield json_data
                            except json.JSONDecodeError:
                                pass  # Ignore non-JSON lines or partial lines
        else:
            # If not streaming, still yield, but only once
            response = await self.client.post(url, url=url, headers=headers, json=payload, timeout=None)
            response.raise_for_status()
            yield response.json() # Yield the single response

    async def get_models(self) -> Dict[str, Any]:
        url = "/api/tags"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def pull_model(self, model_name: str) -> AsyncGenerator[Dict[str, Any], None]:
        url = "/api/pull"
        headers = {"Content-Type": "application/json"}
        payload = {"name": model_name, "stream": True}
        async with self.client.stream("POST", url, headers=headers, json=payload, timeout=None) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                decoded_chunk = chunk.decode("utf-8")
                for line in decoded_chunk.splitlines():
                    try:
                        json_data = json.loads(line)
                        yield json_data
                    except json.JSONDecodeError:
                        pass


# Global client instance, base_url can be updated from config if needed
ollama_client = OllamaClient()