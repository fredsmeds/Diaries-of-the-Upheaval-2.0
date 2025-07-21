# src/data_management/compendium_manager.py

import json
import os
import pandas as pd
from typing import Optional, Dict, Any

class CompendiumManager:
    """
    Manages loading and searching the Tears of the Kingdom compendium data
    from the single COMPENDIUM.json file.
    """
    def __init__(self, data_path: str = "data/compendium/data/COMPENDIUM.json"):
        """
        Initializes the CompendiumManager by loading all data into memory.

        Args:
            data_path: The direct path to the COMPENDIUM.json file.
        """
        self.data_path = data_path
        self.all_entries_df: Optional[pd.DataFrame] = None
        self._load_all_data()

    def _load_all_data(self):
        """
        Loads the main COMPENDIUM.json file into a pandas DataFrame.
        """
        print("--- Loading Compendium Data ---")
        try:
            # Load the single JSON file directly into a pandas DataFrame
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # *** FIX: The JSON file is a list of entries directly, not nested under a 'data' key. ***
            df = pd.DataFrame(data)
            
            self.all_entries_df = df
            # Standardize name column for case-insensitive searching
            self.all_entries_df['search_name'] = self.all_entries_df['name'].str.lower()
            print(f"  - Successfully loaded {len(df)} entries from '{os.path.basename(self.data_path)}'.")
            print("--- Compendium Data Loaded Successfully ---")

        except FileNotFoundError:
            print(f"  - ERROR: '{self.data_path}' not found. Please ensure you have placed COMPENDIUM.json in the correct directory.")
        except (KeyError, TypeError, ValueError): # Added ValueError for broader compatibility
            print(f"  - ERROR: The JSON file at '{self.data_path}' does not have the expected format (it should be a list of objects).")
        except Exception as e:
            print(f"  - An unexpected error occurred loading '{self.data_path}': {e}")

    def find_entry(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Finds a single compendium entry by its name (case-insensitive).

        Args:
            query: The name of the creature, monster, item, etc., to search for.

        Returns:
            A dictionary containing the data for the found entry, or None if not found.
        """
        if self.all_entries_df is None:
            return None

        search_query = query.lower()

        # Search for an exact match first (case-insensitive)
        exact_match = self.all_entries_df[self.all_entries_df['search_name'] == search_query]
        if not exact_match.empty:
            # Convert the row to a dictionary
            return exact_match.iloc[0].to_dict()

        # If no exact match, search for a partial match
        partial_match = self.all_entries_df[self.all_entries_df['search_name'].str.contains(search_query, na=False)]
        if not partial_match.empty:
            return partial_match.iloc[0].to_dict()

        return None

def format_entry_for_agent(entry: Optional[Dict[str, Any]]) -> str:
    """
    Formats a compendium entry dictionary into a clean, readable string for the LLM agent.
    """
    if not entry:
        return "I could not find any information on that subject in the compendium."

    # Clean up the entry data for display (e.g., handle missing values)
    name = entry.get('name', 'N/A').title()
    category = entry.get('category', 'N/A').title()
    description = entry.get('description', 'No description available.')
    
    # Create the base response string
    response = f"Compendium Entry: {name} (Category: {category})\nDescription: {description}"
    
    # Add optional fields if they exist
    locations = entry.get('common_locations')
    if isinstance(locations, list) and locations:
        response += f"\nCommon Locations: {', '.join(locations)}"
        
    drops = entry.get('drops')
    if isinstance(drops, list) and drops:
        response += f"\nDrops: {', '.join(drops)}"
        
    properties = entry.get('properties')
    if isinstance(properties, dict) and properties:
        props_str = ", ".join([f"{key.replace('_', ' ').title()}: {value}" for key, value in properties.items()])
        response += f"\nProperties: {props_str}"

    return response

# --- Main Execution Block (for setup and testing) ---
if __name__ == '__main__':
    print("--- Testing Compendium Manager ---")
    
    # Initialize the manager. It will automatically load the data.
    # Make sure you have placed the downloaded data folder correctly.
    # The structure should be: data/compendium/data/COMPENDIUM.json
    compendium = CompendiumManager()

    if compendium.all_entries_df is not None:
        # Test searching for an entry
        test_queries = ["bokoblin", "silent princess", "royal guard's sword", "nonexistent item"]
        
        for query in test_queries:
            print(f"\n--- Searching for: '{query}' ---")
            found_entry = compendium.find_entry(query)
            
            # Format the result as the agent would see it
            formatted_response = format_entry_for_agent(found_entry)
            print(formatted_response)
    else:
        print("\nTesting aborted as no data was loaded.")
