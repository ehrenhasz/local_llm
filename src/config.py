# src/config.py
import json

SETTINGS = {}

def load_config(file_path="config.json"):
    """Loads the configuration from the specified JSON file."""
    global SETTINGS
    try:
        with open(file_path, 'r') as f:
            SETTINGS = json.load(f)
        print(f"Configuration loaded successfully from {file_path}")
    except FileNotFoundError:
        print(f"ERROR: Configuration file not found at {file_path}")
        SETTINGS = {}
    except json.JSONDecodeError:
        print(f"ERROR: Could not decode JSON from {file_path}")
        SETTINGS = {}

# Load the configuration when the module is first imported
load_config()
