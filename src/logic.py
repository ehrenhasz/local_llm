
import psutil
from pynvml import (
    nvmlInit,
    nvmlDeviceGetCount,
    nvmlDeviceGetHandleByIndex,
    nvmlDeviceGetName,
    nvmlDeviceGetUtilizationRates,
    nvmlDeviceGetMemoryInfo,
    nvmlDeviceGetTemperature,
    NVML_TEMPERATURE_GPU,
    NVMLError,
    nvmlShutdown,
)
import os
import json
import subprocess
import logging

# --- Constants ---
CONFIG_FILE = "./config.json"
RUNNING_MINERS_PID_FILE = "./running_miners.json"
MINER_LOG_FILE_PREFIX = "./miner_"
RECIPES_DIR = "./recipes"

# --- State ---
RUNNING_MINERS = {} # {name: {'process': Popen_object, 'log_file': path, 'config': miner_config}}

import google.generativeai as genai

# --- Logging ---
def log_message(message, level=logging.INFO):
    print(f"[{level}] {message}")

# --- AI Generation ---
def run_llm_generation(api_key, prompt):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        log_message(f"An error occurred during LLM generation: {e}", level=logging.ERROR)
        return f"Error: {e}"

# --- Recipe Logic ---
def get_recipes():
    recipes = {}
    if not os.path.exists(RECIPES_DIR):
        return {}
    for category in os.listdir(RECIPES_DIR):
        category_path = os.path.join(RECIPES_DIR, category)
        if os.path.isdir(category_path):
            recipes[category] = []
            for recipe_file in os.listdir(category_path):
                recipes[category].append(recipe_file)
    return recipes

def read_recipe(category, name):
    recipe_path = os.path.join(RECIPES_DIR, category, name)
    if not os.path.exists(recipe_path):
        return None
    with open(recipe_path, 'r') as f:
        # Simple parsing, assuming a specific format
        lines = f.readlines()
        description = lines[1].replace("Description: ", "").strip()
        prompt = "".join(lines[3:])
        return {"description": description, "prompt": prompt}

# --- System Stats ---
def get_system_stats():
    # ... (code is unchanged) ...
    stats = {
        'cpu': {'percent': 0, 'cores': []},
        'ram': {'percent': 0, 'total': 0, 'used': 0},
        'gpus': []
    }
    try:
        stats['cpu']['percent'] = psutil.cpu_percent()
        stats['cpu']['cores'] = psutil.cpu_percent(percpu=True)
        ram = psutil.virtual_memory()
        stats['ram'] = {'percent': ram.percent, 'total': ram.total, 'used': ram.used}
        nvmlInit()
        device_count = nvmlDeviceGetCount()
        for i in range(device_count):
            handle = nvmlDeviceGetHandleByIndex(i)
            stats['gpus'].append({
                'name': nvmlDeviceGetName(handle),
                'usage': nvmlDeviceGetUtilizationRates(handle).gpu,
                'memory_usage': nvmlDeviceGetUtilizationRates(handle).memory,
                'memory_total': nvmlDeviceGetMemoryInfo(handle).total,
                'memory_used': nvmlDeviceGetMemoryInfo(handle).used,
                'temperature': nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU),
            })
        nvmlShutdown()
    except (NVMLError, psutil.Error):
        pass
    return stats


# --- Miner and Config Logic ---
# ... (code is unchanged) ...
def save_running_miners():
    pids = {name: info['process'].pid for name, info in RUNNING_MINERS.items() if isinstance(info['process'], subprocess.Popen)}
    with open(RUNNING_MINERS_PID_FILE, 'w') as f:
        json.dump(pids, f, indent=2)

def load_running_miners():
    if not os.path.exists(RUNNING_MINERS_PID_FILE): return
    try:
        with open(RUNNING_MINERS_PID_FILE, 'r') as f:
            pids = json.load(f)
    except json.JSONDecodeError:
        return
    config = read_config()
    for name, pid in pids.items():
        if psutil.pid_exists(pid):
            miner_config = next((m for m in config['miners'] if m['name'] == name), None)
            if miner_config:
                RUNNING_MINERS[name] = {'process': psutil.Process(pid), 'log_file': f"{MINER_LOG_FILE_PREFIX}{name}.log", 'config': miner_config}
    save_running_miners()

def read_config():
    if not os.path.exists(CONFIG_FILE): return {"miners": []}
    with open(CONFIG_FILE, 'r') as f: return json.load(f)

def write_config(config):
    with open(CONFIG_FILE, 'w') as f: json.dump(config, f, indent=4)

def start_miner(miner_config):
    name = miner_config['name']
    if not os.path.exists(miner_config['miner_path']): return False, "Executable not found"
    args = [miner_config['miner_path'], "-a", miner_config['coin'], "-o", miner_config['pool'], "-u", miner_config['wallet'], "-w", miner_config['worker']]
    if miner_config.get('device') is not None: args.extend(["--cuda-devices", str(miner_config['device'])])
    log_file = f"{MINER_LOG_FILE_PREFIX}{name}.log"
    with open(log_file, 'w') as log_f:
        proc = subprocess.Popen(args, stdout=log_f, stderr=subprocess.STDOUT, creationflags=subprocess.DETACHED_PROCESS if os.name == 'nt' else 0)
    RUNNING_MINERS[name] = {'process': proc, 'log_file': log_file, 'config': miner_config}
    save_running_miners()
    return True, f"Started miner '{name}'"

def stop_miner(name):
    if name not in RUNNING_MINERS: return False, "Not running"
    try:
        p = psutil.Process(RUNNING_MINERS[name]['process'].pid)
        p.terminate()
        p.wait(timeout=5)
    except psutil.NoSuchProcess: pass
    except psutil.TimeoutExpired: p.kill()
    del RUNNING_MINERS[name]
    save_running_miners()
    return True, f"Stopped miner '{name}'"
