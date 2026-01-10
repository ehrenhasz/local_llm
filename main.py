import click
import os
import logging
from datetime import datetime
import shutil
import json
import platform
import subprocess # Import subprocess for launching miners
import time # For time.sleep in simulations if needed
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

import src.ai_mode as ai_mode # Import ai_mode

# --- Logging Setup ---
LOG_FILE = "./local_llm.log"
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='[%(asctime)s] [%(levelname)s] - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

def log_message(message, level=logging.INFO):
    logging.log(level, message)

MINER_TEMP_FILE_PREFIX = "./temp_miner_" # Prefix for unique temp files per miner
MINER_LOG_FILE_PREFIX = "./miner_" # Prefix for unique miner log files
CONFIG_FILE = "./config.json"
RUNNING_MINERS_PID_FILE = "./running_miners.json"

RUNNING_MINERS = {} # Dictionary to store running miner processes {name: {'process': Popen_object, 'log_file': path, 'config': miner_config}}

def save_running_miners():
    """Saves the PIDs of running miners to a file."""
    pids = {name: info['process'].pid for name, info in RUNNING_MINERS.items()}
    with open(RUNNING_MINERS_PID_FILE, 'w') as f:
        json.dump(pids, f, indent=2)

def load_running_miners():
    """Loads running miner processes from the PID file."""
    if not os.path.exists(RUNNING_MINERS_PID_FILE):
        return

    with open(RUNNING_MINERS_PID_FILE, 'r') as f:
        try:
            pids = json.load(f)
        except json.JSONDecodeError:
            return # Ignore if the file is corrupted

    config = read_config()
    for name, pid in pids.items():
        if psutil.pid_exists(pid):
            miner_config = next((m for m in config['miners'] if m['name'] == name), None)
            if miner_config:
                process = psutil.Process(pid)
                # We can't get the Popen object back, but we can manage the process with psutil
                RUNNING_MINERS[name] = {'process': process, 'log_file': f"{MINER_LOG_FILE_PREFIX}{name}.log", 'config': miner_config}
                log_message(f"Resumed monitoring of miner '{name}' (PID: {pid}).")
        else:
            log_message(f"Miner '{name}' (PID: {pid}) was not running.", level=logging.WARN)

    save_running_miners() # Clean up PID file from non-running processes

def read_config():
    if not os.path.exists(CONFIG_FILE):
        return {"miners": []}
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        # Handle old config.json format
        if "miners" not in config and "miner_path" in config:
            log_message("Migrating old config.json format to new format.", level=logging.INFO)
            old_config = {
                "name": "default-miner",
                "miner_path": config.get("miner_path"),
                "wallet": config.get("wallet"),
                "pool": config.get("pool"),
                "coin": config.get("coin"),
                "worker": config.get("worker"),
                "device": None # Assuming single device or needs to be specified
            }
            return {"miners": [old_config]}
        return config

def write_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def _start_miner(miner_config):
    """Starts a single crypto miner process using subprocess."""
    name = miner_config['name']
    miner_path = miner_config['miner_path']
    wallet = miner_config['wallet']
    pool = miner_config['pool']
    coin = miner_config['coin']
    worker = miner_config['worker']
    device = miner_config.get('device')
    
    miner_log_file = f"{MINER_LOG_FILE_PREFIX}{name}.log"

    try:
        log_message(f"Attempting to start crypto miner '{name}'...")
        click.echo(f"Attempting to start crypto miner '{name}'...")

        command_args = [miner_path, "-a", coin, "-o", pool, "-u", wallet, "-p", "x", "-w", worker]
        if device is not None:
            # T-Rex specific argument for CUDA device selection
            command_args.extend(["--cuda-devices", str(device)]) 
        
        # Ensure miner_path is executable and exists
        if not os.path.exists(miner_path):
            raise FileNotFoundError(f"Miner executable not found at: {miner_path}")

        # Open log file for stdout/stderr redirection
        with open(miner_log_file, 'w') as log_f:
            process = subprocess.Popen(
                command_args,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.DETACHED_PROCESS if os.name == 'nt' else 0 # Detach process on Windows
            )
        
        RUNNING_MINERS[name] = {'process': process, 'log_file': miner_log_file, 'config': miner_config}
        log_message(f"Miner '{name}' started (PID: {process.pid}). Output redirected to {miner_log_file}")
        click.echo(f"Miner '{name}' started (PID: {process.pid}). Output redirected to {miner_log_file}")
        save_running_miners()

    except FileNotFoundError as e:
        log_message(f"Error starting miner '{name}': {e}", level=logging.ERROR)
        click.echo(f"Error starting miner '{name}': {e}. Please ensure miner_path is correct and executable.")
    except Exception as e:
        log_message(f"An unexpected error occurred while starting miner '{name}': {e}", level=logging.ERROR)
        click.echo(f"An unexpected error occurred while starting miner '{name}': {e}")

def _stop_miner(name):
    """Stops a single crypto miner process."""
    try:
        if name in RUNNING_MINERS:
            miner_info = RUNNING_MINERS[name]
            process = miner_info['process']

            log_message(f"Stopping crypto miner '{name}' (PID: {process.pid})...")
            click.echo(f"Stopping crypto miner '{name}' (PID: {process.pid})...")

            if isinstance(process, subprocess.Popen):
                process.terminate()
                process.wait(timeout=10) # Give it 10 seconds to terminate gracefully

                if process.poll() is None: # If still running, force kill
                    process.kill()
                    process.wait()
                    log_message(f"Miner '{name}' (PID: {process.pid}) force-killed.", level=logging.WARN)
                    click.echo(f"Miner '{name}' (PID: {process.pid}) force-killed.")
            elif isinstance(process, psutil.Process):
                process.terminate()
                try:
                    process.wait(timeout=10)
                except psutil.TimeoutExpired:
                    process.kill()
                    process.wait()
                    log_message(f"Miner '{name}' (PID: {process.pid}) force-killed.", level=logging.WARN)
                    click.echo(f"Miner '{name}' (PID: {process.pid}) force-killed.")


            del RUNNING_MINERS[name]
            log_message(f"Miner '{name}' (PID: {process.pid}) stopped.")
            click.echo(f"Miner '{name}' (PID: {process.pid}) stopped.")
            save_running_miners()
        else:
            log_message(f"Miner '{name}' not found in running processes.", level=logging.WARN)
            click.echo(f"Miner '{name}' not found in running processes.")

    except Exception as e:
        log_message(f"An error occurred while stopping miner '{name}': {e}", level=logging.ERROR)
        click.echo(f"An error occurred while stopping miner '{name}': {e}")

@click.group()
def cli():
    """local_llm Controller"""
    load_running_miners()
    pass

@cli.command()
def ai():
    """Starts AI Mode"""
    log_message("Starting AI Mode...")
    click.echo("Starting AI Mode...")
    ai_mode.start_llm() # Call start_llm from ai_mode
    click.echo("Press Enter to continue...")
    input()
    ai_mode.stop_llm() # Call stop_llm from ai_mode


@cli.command()
def crypto():
    """Starts Crypto Mode"""
    log_message("Starting Crypto Mode (multiple miners)....")
    click.echo("Starting Crypto Mode (multiple miners)....")
    
    config = read_config()
    if not config['miners']:
        log_message("No miner configurations found in config.json. Cannot start crypto mode.", level=logging.ERROR)
        click.echo("No miner configurations found in config.json. Cannot start crypto mode.")
        return

    for miner_config in config['miners']:
        if miner_config['name'] in RUNNING_MINERS:
            log_message(f"Miner '{miner_config['name']}' is already running.", level=logging.WARN)
            click.echo(f"Miner '{miner_config['name']}' is already running.")
            continue
        _start_miner(miner_config)

@cli.command(name="stop-crypto")
def stop_crypto():
    """Stops all running miners."""
    log_message("Stopping all miners...")
    click.echo("Stopping all miners...")
    for miner_name in list(RUNNING_MINERS.keys()): # Iterate over a copy as dict changes size during iteration
        _stop_miner(miner_name)


@cli.command()
def setup():
    """Runs the setup script"""
    log_message("Running setup...")
    click.echo("Running setup...")

    system = platform.system()
    if system == "Windows":
        MINER_URL = "https://github.com/trexminer/T-Rex/releases/download/0.26.8/t-rex-0.26.8-win.zip"
        MINER_ZIP = "t-rex.zip"
        MINER_EXE = "t-rex.exe"
    elif system == "Linux":
        MINER_URL = "https://github.com/trexminer/T-Rex/releases/download/0.26.8/t-rex-0.26.8-linux.tar.gz"
        MINER_ZIP = "t-rex.tar.gz"
        MINER_EXE = "t-rex"
    else:
        click.echo(f"Unsupported OS: {system}")
        return

    MINER_DIR = "./bin/t-rex"

    try:
        if not os.path.exists(MINER_DIR):
            log_message(f"Creating miner directory: {MINER_DIR}")
            os.makedirs(MINER_DIR)
            click.echo(f"Creating miner directory: {MINER_DIR}")

        log_message(f"Downloading T-Rex miner for {system}...")
        click.echo(f"Downloading T-Rex miner for {system}...")
        # Simulate download and extraction
        # In a real scenario, you would use requests to download and zipfile/tarfile to extract
        with open(os.path.join(MINER_DIR, MINER_EXE), "w") as f:
            f.write(f"DUMMY_T_REX_EXE_CONTENT_FOR_{system}")

        log_message("T-Rex miner setup complete.")
        click.echo("T-Rex miner setup complete.")

    except Exception as e:
        log_message(f"An error occurred during setup: {e}", level=logging.ERROR)
        click.echo(f"An error occurred during setup: {e}")

@cli.command()
def backup():
    """Backs up configuration"""
    log_message("Running backup...")
    click.echo("Running backup...")

    try:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_file = f"config.json.{timestamp}.bak"
        config_file = "./config.json"

        if os.path.exists(config_file):
            log_message(f"Backing up {config_file} to {backup_file}")
            shutil.copy(config_file, backup_file)
            click.echo(f"Backing up {config_file} to {backup_file}")
            log_message("Backup complete.")
            click.echo("Backup complete.")
        else:
            log_message(f"config.json not found, skipping backup.", level=logging.WARN)
            click.echo(f"config.json not found, skipping backup.")

    except Exception as e:
        log_message(f"An error occurred during backup: {e}", level=logging.ERROR)
        click.echo(f"An error occurred during backup: {e}")

@cli.command()
def cleanup():
    """Cleans up temporary files"""
    log_message("Running cleanup...")
    click.echo("Running cleanup...")

    temp_files = [
        ai_mode.LLM_PID_FILE, # Use LLM_PID_FILE from ai_mode
        RUNNING_MINERS_PID_FILE,
    ]
    # Add all miner temp files and log files to cleanup
    for file_name in os.listdir('.'):
        if file_name.startswith(MINER_TEMP_FILE_PREFIX) and file_name.endswith(".tmp"):
            temp_files.append(file_name)
        if file_name.startswith(MINER_LOG_FILE_PREFIX) and file_name.endswith(".log"):
            temp_files.append(file_name)

    for file_path in temp_files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                log_message(f"Removed temporary file: {file_path}")
                click.echo(f"Removed temporary file: {file_path}")
            except Exception as e:
                log_message(f"Error removing temporary file: {file_path}. Error: {e}", level=logging.ERROR)
                click.echo(f"Error removing temporary file: {file_path}. Error: {e}")
        else:
            log_message(f"Temporary file not found: {file_path}", level=logging.INFO)
            click.echo(f"Temporary file not found: {file_path}")

    log_message("Temporary file cleanup complete.")
    click.echo("Temporary file cleanup complete.")


@click.group()
def config_miner():
    """Manages miner configurations."""
    pass

@config_miner.command(name="add")
@click.option('--name', required=True, help="Name of the miner configuration.")
@click.option('--miner-path', help="Path to the miner executable.")
@click.option('--wallet', required=True, help="Wallet address for mining.")
@click.option('--pool', required=True, help="Mining pool address and port (e.g., 'stratum+tcp://pool.zano.org:3333').")
@click.option('--coin', required=True, help="Coin to mine (e.g., 'zano').")
@click.option('--worker', default="gemini-worker", help="Worker name.")
@click.option('--device', type=int, help="GPU device ID (e.g., 0, 1).")
def add(name, miner_path, wallet, pool, coin, worker, device):
    """Adds a new miner configuration."""
    if miner_path is None:
        system = platform.system()
        if system == "Windows":
            miner_path = "./bin/t-rex/t-rex.exe"
        elif system == "Linux":
            miner_path = "./bin/t-rex/t-rex"
        else:
            click.echo(f"Unsupported OS: {system}. Please provide the miner path manually using --miner-path.")
            return

    config = read_config()
    if any(m['name'] == name for m in config['miners']):
        log_message(f"Miner configuration with name '{name}' already exists. Use 'update' to modify.", level=logging.WARN)
        click.echo(f"Miner configuration with name '{name}' already exists. Use 'update' to modify.")
        return

    new_miner = {
        "name": name,
        "miner_path": miner_path,
        "wallet": wallet,
        "pool": pool,
        "coin": coin,
        "worker": worker,
        "device": device
    }
    config['miners'].append(new_miner)
    write_config(config)
    log_message(f"Added miner configuration: {name}")
    click.echo(f"Added miner configuration: {name}")

@config_miner.command()
@click.option('--name', required=True, help="Name of the miner configuration to remove.")
def remove(name):
    """Removes a miner configuration."""
    config = read_config()
    initial_miner_count = len(config['miners'])
    config['miners'] = [m for m in config['miners'] if m['name'] != name]
    if len(config['miners']) < initial_miner_count:
        write_config(config)
        log_message(f"Removed miner configuration: {name}")
        click.echo(f"Removed miner configuration: {name}")
    else:
        log_message(f"Miner configuration with name '{name}' not found.", level=logging.WARN)
        click.echo(f"Miner configuration with name '{name}' not found.")

@config_miner.command(name="list")
def list_miners():
    """Lists all miner configurations."""
    config = read_config()
    if not config['miners']:
        log_message("No miner configurations found.", level=logging.INFO)
        click.echo("No miner configurations found.")
        return

    click.echo("\n--- Miner Configurations ---")
    for i, miner in enumerate(config['miners']):
        click.echo(f"  {i+1}. Name: {miner['name']}")
        click.echo(f"     Path: {miner['miner_path']}")
        click.echo(f"     Wallet: {miner['wallet']}")
        click.echo(f"     Pool: {miner['pool']}")
        click.echo(f"     Coin: {miner['coin']}")
        click.echo(f"     Worker: {miner['worker']}")
        click.echo(f"     Device: {miner['device']}")
        click.echo("----------------------------")
    log_message("Listed all miner configurations.")

@config_miner.command()
@click.option('--name', required=True, help="Name of the miner configuration to update.")
@click.option('--miner-path', help="New path to the miner executable.")
@click.option('--wallet', help="New wallet address for mining.")
@click.option('--pool', help="New mining pool address and port.")
@click.option('--coin', help="New coin to mine.")
@click.option('--worker', help="New worker name.")
@click.option('--device', type=int, help="New GPU device ID.")
def update(name, miner_path, wallet, pool, coin, worker, device):
    """Updates an existing miner configuration."""
    config = read_config()
    updated = False
    for miner in config['miners']:
        if miner['name'] == name:
            if miner_path is not None:
                miner['miner_path'] = miner_path
            if wallet is not None:
                miner['wallet'] = wallet
            if pool is not None:
                miner['pool'] = pool
            if coin is not None:
                miner['coin'] = coin
            if worker is not None:
                miner['worker'] = worker
            if device is not None:
                miner['device'] = device
            updated = True
            break
    
    if updated:
        write_config(config)
        log_message(f"Updated miner configuration: {name}")
        click.echo(f"Updated miner configuration: {name}")
    else:
        log_message(f"Miner configuration with name '{name}' not found.", level=logging.WARN)
        click.echo(f"Miner configuration with name '{name}' not found.")

@cli.command()
def dashboard():
    """Displays a real-time system resource dashboard."""
    try:
        nvmlInit()
        device_count = nvmlDeviceGetCount()

        while True:
            click.clear()
            click.echo("--- System Resource Dashboard ---")
            
            # --- CPU Info ---
            cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
            click.echo(f"\nCPU Usage: {psutil.cpu_percent()}%")
            for i, core_percent in enumerate(cpu_percent):
                click.echo(f"  Core {i}: {core_percent}%")

            # --- RAM Info ---
            ram = psutil.virtual_memory()
            click.echo(f"\nRAM Usage: {ram.percent}%")
            click.echo(f"  Total: {ram.total / (1024**3):.2f} GB")
            click.echo(f"  Used: {ram.used / (1024**3):.2f} GB")
            click.echo(f"  Free: {ram.free / (1024**3):.2f} GB")
            
            # --- GPU Info ---
            for i in range(device_count):
                handle = nvmlDeviceGetHandleByIndex(i)
                gpu_name = nvmlDeviceGetName(handle)
                util = nvmlDeviceGetUtilizationRates(handle)
                mem = nvmlDeviceGetMemoryInfo(handle)
                temp = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)

                click.echo(f"\nGPU {i}: {gpu_name}")
                click.echo(f"  Usage: {util.gpu}%")
                click.echo(f"  Memory: {util.memory}%")
                click.echo(f"  Memory Total: {mem.total / (1024**2):.2f} MB")
                click.echo(f"  Memory Used: {mem.used / (1024**2):.2f} MB")
                click.echo(f"  Temperature: {temp}°C")

            click.echo("\nPress Ctrl+C to exit dashboard.")
            time.sleep(2)

    except NVMLError as error:
        click.echo(f"Failed to initialize NVIDIA Management Library: {error}")
        click.echo("Please ensure NVIDIA drivers are installed.")
    except KeyboardInterrupt:
        click.echo("\nExiting dashboard.")
    finally:
        try:
            nvmlShutdown()
        except:
            pass

@click.group()
def recipe():
    """Manages recipes."""
    pass

@recipe.command(name="list")
def list_recipes():
    """Lists all available recipes."""
    recipes_dir = "./recipes"
    if not os.path.exists(recipes_dir):
        click.echo("Recipes directory not found.")
        return

    click.echo("\n--- Available Recipes ---")
    for category in os.listdir(recipes_dir):
        category_path = os.path.join(recipes_dir, category)
        if os.path.isdir(category_path):
            click.echo(f"\nCategory: {category}")
            for recipe_file in os.listdir(category_path):
                click.echo(f"  - {recipe_file}")
    click.echo("\n-------------------------")

@recipe.command(name="add")
@click.option('--category', required=True, help="Category of the recipe.")
@click.option('--name', required=True, help="Name of the recipe file (e.g., my_recipe.txt).")
@click.option('--description', required=True, help="Description of the recipe.")
@click.option('--prompt', required=True, help="The prompt for the recipe.")
def add_recipe(category, name, description, prompt):
    """Adds a new recipe."""
    recipes_dir = "./recipes"
    category_path = os.path.join(recipes_dir, category)
    if not os.path.exists(category_path):
        os.makedirs(category_path)

    recipe_path = os.path.join(category_path, name)
    if os.path.exists(recipe_path):
        click.echo(f"Recipe '{name}' already exists in category '{category}'.")
        return

    content = f"Recipe: {name}\nDescription: {description}\nPrompt:\n{prompt}"
    with open(recipe_path, 'w') as f:
        f.write(content)
    click.echo(f"Added recipe '{name}' to category '{category}'.")


@recipe.command(name="remove")
@click.option('--path', required=True, help="Path to the recipe file to remove (e.g., 'boilerplate_code/my_recipe.txt').")
def remove_recipe(path):
    """Removes a recipe."""
    recipe_path = os.path.join("./recipes", path)
    if not os.path.exists(recipe_path):
        click.echo(f"Recipe not found at '{recipe_path}'.")
        return

    os.remove(recipe_path)
    click.echo(f"Removed recipe at '{recipe_path}'.")

@recipe.command(name="update")
@click.option('--path', required=True, help="Path to the recipe file to update (e.g., 'boilerplate_code/my_recipe.txt').")
@click.option('--description', help="New description for the recipe.")
@click.option('--prompt', help="New prompt for the recipe.")
def update_recipe(path, description, prompt):
    """Updates a recipe."""
    recipe_path = os.path.join("./recipes", path)
    if not os.path.exists(recipe_path):
        click.echo(f"Recipe not found at '{recipe_path}'.")
        return

    #This is a simple implementation. A more robust one would parse the file and replace the fields.
    #For now, we'll just overwrite the file if new content is provided.
    if description or prompt:
        with open(recipe_path, 'r') as f:
            lines = f.readlines()

        #This is a very basic parsing. It assumes the format is consistent.
        name = lines[0].replace("Recipe: ", "").strip()
        new_content = f"Recipe: {name}\n"
        if description:
            new_content += f"Description: {description}\n"
        else:
            new_content += lines[1]

        if prompt:
            new_content += f"Prompt:\n{prompt}\n"
        else:
            new_content += "".join(lines[2:])


        with open(recipe_path, 'w') as f:
            f.write(new_content)
        click.echo(f"Updated recipe at '{recipe_path}'.")
    else:
        click.echo("Nothing to update. Please provide a new description or prompt.")

cli.add_command(config_miner)
cli.add_command(recipe)

if __name__ == '__main__':
    cli()
