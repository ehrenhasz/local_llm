import psutil
import platform
import subprocess
import json
from typing import Dict, Any, List

def get_cpu_stats() -> Dict[str, Any]:
    return {
        "percent": psutil.cpu_percent(interval=1),
        "cores": psutil.cpu_count(logical=False),
        "threads": psutil.cpu_count(logical=True),
    }

def get_ram_stats() -> Dict[str, Any]:
    mem = psutil.virtual_memory()
    return {
        "total": mem.total,
        "available": mem.available,
        "percent": mem.percent,
        "used": mem.used,
        "free": mem.free,
    }

def get_gpu_stats() -> List[Dict[str, Any]]:
    gpus = []
    if platform.system() == "Windows":
        try:
            # Try to get GPU info via WMIC for NVIDIA/AMD
            # This is a best-effort approach; direct driver interaction is complex
            output = subprocess.check_output(
                ["wmic", "path", "Win32_VideoController", "get", "Name,AdapterRAM"],
                text=True, creationflags=subprocess.CREATE_NO_WINDOW
            ).strip().split("\n")
            
            for line in output[1:]:
                parts = line.strip().split() # Split by whitespace
                if len(parts) >= 2: # Expect at least Name and AdapterRAM
                    name = " ".join(parts[:-1]) # Name might have spaces
                    try:
                        ram_mb = int(parts[-1]) / (1024**2) # AdapterRAM is in bytes
                        gpus.append({"name": name, "memory_total_mb": round(ram_mb, 2), "usage": 0, "memory_usage": 0, "temperature": 0})
                    except ValueError:
                        # Handle cases where AdapterRAM might not be a clean number
                        gpus.append({"name": name, "memory_total_mb": None, "usage": 0, "memory_usage": 0, "temperature": 0})
        except Exception:
            pass # Fallback to generic if WMIC fails
    
    # Attempt to use nvidia-smi if available
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=gpu_name,memory.total,memory.used,utilization.gpu,temperature.gpu", "--format=csv,nounits,noheader"],
            text=True, creationflags=subprocess.CREATE_NO_WINDOW
        ).strip().split("\n")
        for line in output:
            if line.strip():
                parts = line.split(', ')
                if len(parts) == 5:
                    name = parts[0]
                    mem_total_mb = int(parts[1])
                    mem_used_mb = int(parts[2])
                    gpu_util = int(parts[3])
                    temp_c = int(parts[4])
                    gpus.append({
                        "name": name,
                        "memory_total_mb": mem_total_mb,
                        "memory_used_mb": mem_used_mb,
                        "usage": gpu_util,
                        "memory_usage": round((mem_used_mb / mem_total_mb) * 100, 2) if mem_total_mb > 0 else 0,
                        "temperature": temp_c,
                    })
        return gpus # If nvidia-smi works, return its output
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass # nvidia-smi not found or failed

    # Attempt to use roc-smi if available (for AMD GPUs on Linux)
    if platform.system() == "Linux":
        try:
            output = subprocess.check_output(["roc-smi", "--json"], text=True).strip()
            data = json.loads(output)
            for gpu_info in data:
                gpus.append({
                    "name": gpu_info.get("GPU_ID", "AMD GPU"),
                    "memory_total_mb": round(gpu_info.get("VRAM Total (MB)", 0), 2),
                    "memory_used_mb": round(gpu_info.get("VRAM Usage (MB)", 0), 2),
                    "usage": round(gpu_info.get("GPU Use (%)", 0), 2),
                    "memory_usage": round(gpu_info.get("VRAM Usage (%)", 0), 2),
                    "temperature": round(gpu_info.get("GPU Temp (C)", 0), 2),
                })
            return gpus # If roc-smi works, return its output
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
            pass # roc-smi not found or failed

    # Generic fallback if no specific GPU tool is found
    if not gpus: # Only add generic if no specific GPU info was gathered
        try:
            # On Linux, try lspci if no other method worked.
            if platform.system() == "Linux":
                output = subprocess.check_output(["lspci", "-vmmd", "::0300"], text=True).strip().split("\n\n")
                for device_block in output:
                    if device_block.strip():
                        name = "Unknown GPU"
                        for line in device_block.split("\n"):
                            if line.startswith("Device:"):
                                name = line.split('\t', 1)[1]
                        gpus.append({"name": name, "memory_total_mb": None, "usage": 0, "memory_usage": 0, "temperature": 0})
            elif platform.system() == "Darwin": # macOS
                # More complex on macOS, might need external tools or specific frameworks.
                # For now, a placeholder.
                gpus.append({"name": "macOS GPU", "memory_total_mb": None, "usage": 0, "memory_usage": 0, "temperature": 0})
            elif not gpus: # If still no GPUs identified, add a generic entry.
                 gpus.append({"name": "Generic GPU", "memory_total_mb": None, "usage": 0, "memory_usage": 0, "temperature": 0})
        except (subprocess.CalledProcessError, FileNotFoundError):
            gpus.append({"name": "Generic GPU", "memory_total_mb": None, "usage": 0, "memory_usage": 0, "temperature": 0})

    return gpus

def get_system_stats() -> Dict[str, Any]:
    return {
        "cpu": get_cpu_stats(),
        "ram": get_ram_stats(),
        "gpus": get_gpu_stats(),
        "timestamp": psutil.boot_time(),
    }
