# src/crypto_mode.py
import subprocess
import os
from . import config

def start():
    """Starts the crypto miner as a background process."""
    print("Attempting to start the crypto miner...")

    # Ensure config is loaded and has necessary keys
    if not config.SETTINGS:
        print("ERROR: Configuration is not loaded.")
        return

    # Check if running inside a container and set miner path accordingly
    if os.getenv("IN_CONTAINER") == "true":
        miner_path = "/app/t-rex"
    else:
        miner_path = config.SETTINGS.get("miner_path")

    coin = config.SETTINGS.get("coin")
    pool = config.SETTINGS.get("pool")
    wallet = config.SETTINGS.get("wallet")
    worker = config.SETTINGS.get("worker")

    if not all([miner_path, coin, pool, wallet, worker]):
        print("ERROR: One or more required miner settings are missing or could not be determined.")
        return

    command = [
        miner_path,
        "-a", coin,
        "-o", pool,
        "-u", wallet,
        "-p", "x",
        "-w", worker
    ]

    try:
        print(f"Executing command: {' '.join(command)}")
        # Use Popen to start the miner as a non-blocking background process
        # In a container, we might want to run this in the foreground, but for now...
        # let's keep the behavior consistent.
        subprocess.Popen(command) # Simplified for container, assuming it runs in the foreground of the entrypoint
        print("Crypto miner process has been started.")
    except FileNotFoundError:
        print(f"ERROR: Miner executable not found at '{miner_path}'.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
