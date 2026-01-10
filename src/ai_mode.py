# src/ai_mode.py
import os
import logging
import time

# --- Logging Setup (assuming main.py handles basicConfig, so just get logger) ---
logger = logging.getLogger(__name__)

LLM_PID_FILE = "./llm_server.pid" # Using a .pid file to simulate a running process

def start_llm():
    """Simulates starting the LLM server."""
    try:
        if os.path.exists(LLM_PID_FILE):
            logger.warning("LLM server appears to be already running (PID file exists).")
            print("LLM server appears to be already running.")
            return

        pid = os.getpid() # Simulate a PID for the LLM server
        with open(LLM_PID_FILE, "w") as f:
            f.write(str(pid))
        
        logger.info(f"LLM server simulation started. PID: {pid}. PID file: {LLM_PID_FILE}")
        print(f"LLM server simulation started. PID: {pid}")

        # Simulate some startup time
        time.sleep(2) 
        print("LLM server is ready.")

    except Exception as e:
        logger.error(f"An error occurred while starting LLM server simulation: {e}")
        print(f"An error occurred while starting LLM server simulation: {e}")

def stop_llm():
    """Simulates stopping the LLM server."""
    try:
        if os.path.exists(LLM_PID_FILE):
            with open(LLM_PID_FILE, "r") as f:
                pid = f.read().strip()
            
            os.remove(LLM_PID_FILE)
            logger.info(f"LLM server simulation stopped. PID file removed: {LLM_PID_FILE} (simulated PID: {pid})")
            print(f"LLM server simulation stopped.")

        else:
            logger.info("No LLM server PID file found. Server not running or already stopped.")
            print("LLM server not running or already stopped.")

    except Exception as e:
        logger.error(f"An error occurred while stopping LLM server simulation: {e}")
        print(f"An error occurred while stopping LLM server simulation: {e}")