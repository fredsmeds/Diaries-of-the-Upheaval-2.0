# src/data_management/compendium_manager.py
import json
import os
import logging

# Basic Configuration
logging.basicConfig(level=logging.INFO)

# Path Definitions
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data', 'compendium', 'data')
COMPENDIUM_FILE = os.path.join(DATA_DIR, 'COMPENDIUM.json')

class CompendiumManager:
    def __init__(self):
        self.entries = self._load_compendium()

    def _load_compendium(self):
        logging.info("--- Loading Compendium Data (v4 - Final) ---")
        try:
            with open(COMPENDIUM_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logging.info(" - Correcting image URLs...")
            
            # This handles both flat and nested structures
            def correct_urls_recursive(obj):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if key == 'image' and isinstance(value, str) and value.startswith('./images/'):
                            obj[key] = value.replace(
                                './images/',
                                'https://raw.githubusercontent.com/fredsmeds/Diaries-of-the-Upheaval-2.0/main/data/compendium/images/'
                            )
                        else:
                            correct_urls_recursive(value)
                elif isinstance(obj, list):
                    for item in obj:
                        correct_urls_recursive(item)

            correct_urls_recursive(data)
            
            logging.info(f" - Successfully loaded and processed entries from '{os.path.basename(COMPENDIUM_FILE)}'.")
            logging.info("--- Compendium Data Loaded Successfully ---")
            return data
        except FileNotFoundError:
            logging.error(f"FATAL: Compendium file not found at {COMPENDIUM_FILE}")
            return {}
        except Exception as e:
            logging.error(f"Error loading compendium: {e}")
            return {}

    def find_entry(self, query: str):
        """
        Recursively searches for a compendium entry by name in a potentially nested dictionary.
        """
        if not self.entries:
            return None
            
        query = query.lower().strip()
        
        def search_recursive(data):
            if isinstance(data, dict):
                # Check if the current dictionary is a valid entry
                if 'name' in data and query in data['name'].lower():
                    return data
                # If not, search through its values
                for value in data.values():
                    result = search_recursive(value)
                    if result:
                        return result
            elif isinstance(data, list):
                for item in data:
                    result = search_recursive(item)
                    if result:
                        return result
            return None

        found_entry = search_recursive(self.entries)
        if found_entry:
            logging.info(f"Found entry for '{query}'")
        else:
            logging.warning(f"No entry found for query: '{query}'")
        
        return found_entry


def format_entry_for_agent(entry: dict | None) -> dict:
    """
    Formats a compendium entry into a structured dictionary for the agent.
    """
    if not entry:
        return {"description": "I could not find any information on that in the archives.", "image_url": None}
    
    description = entry.get('description', 'No description available.')
    image_url = entry.get('image', None)
    
    return {"description": description, "image_url": image_url}
