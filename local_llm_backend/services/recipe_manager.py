import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Correctly determine the base path for data files (like the recipes dir)
# for both development and PyInstaller bundled mode.
if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the base path is the temp directory
    # where PyInstaller unpacks the data files.
    base_path = Path(sys._MEIPASS)
else:
    # In a normal environment, the base path is the project root
    base_path = Path(__file__).parent.parent.parent

RECIPES_DIR = base_path / "recipes"

def get_recipes() -> Dict[str, List[str]]:
    recipes = {}
    if not RECIPES_DIR.is_dir():
        return {}

    for category_path in RECIPES_DIR.iterdir():
        if category_path.is_dir():
            category_name = category_path.name
            recipes[category_name] = []
            for recipe_file in category_path.iterdir():
                if recipe_file.is_file() and recipe_file.suffix == '.txt': # Assuming recipe files are .txt
                    recipes[category_name].append(recipe_file.stem) # Use stem to get filename without extension
    return recipes

def read_recipe(category: str, name: str) -> Optional[Dict[str, str]]:
    recipe_file_path = RECIPES_DIR / category / f"{name}.txt"
    if not recipe_file_path.is_file():
        return None
    try:
        with open(recipe_file_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Simple parsing, assuming first line is description, rest is prompt
            lines = content.splitlines()
            description = lines[0].strip() if lines else ""
            prompt = "\n".join(lines[1:]).strip()
            return {"description": description, "prompt": prompt}
    except Exception as e:
        print(f"Error reading recipe {category}/{name}: {e}")
        return None
