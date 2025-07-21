# src/data_management/compendium_manager.py

import json
import os
import pandas as pd
from typing import Optional, Dict, Any

# *** NEW: Define the base URL for your GitHub repository's raw content. ***
# This will be used to construct the correct, working image links.
# Make sure your username and repository name are correct. We'll assume the branch is 'main'.
GITHUB_USER = "fredsmeds"
REPO_NAME = "Diaries-of-the-Upheaval-2.0"
BRANCH_NAME = "main"
# This is the local path where you stored the images from the other repository
LOCAL_IMAGE_PATH_PREFIX = "data/compendium/images/"
GITHUB_BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/{BRANCH_NAME}/{LOCAL_IMAGE_PATH_PREFIX}"


class CompendiumManager:
    """
    Manages loading and searching the Tears of the Kingdom compendium data
    from the COMPENDIUM.json file.
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
        Loads the main COMPENDIUM.json file and corrects the image paths.
        """
        print("--- Loading Compendium Data ---")
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)

            raw_data.pop('info', None)
            entries_dict = raw_data

            entries_list = []
            for name, details in entries_dict.items():
                details['id_name'] = name 
                entries_list.append(details)

            df = pd.DataFrame(entries_list)
            self.all_entries_df = df
            self.all_entries_df['search_name'] = self.all_entries_df['name'].str.lower()
            
            # --- *** FIX: Correct the Image URLs *** ---
            print("  - Correcting image URLs to point to local/GitHub repository...")
            
            # Function to extract filename and create a new URL
            def create_new_url(old_url):
                if pd.notna(old_url):
                    # Takes "https://.../images/Animal_Bear_A_Icon.png" and returns "Animal_Bear_A_Icon.png"
                    filename = os.path.basename(old_url)
                    return f"{GITHUB_BASE_URL}{filename}"
                return None

            # Apply this function to the 'image' and 'thumbnail' columns
            self.all_entries_df['corrected_image_url'] = self.all_entries_df['image'].apply(create_new_url)
            self.all_entries_df['corrected_thumbnail_url'] = self.all_entries_df['thumbnail'].apply(create_new_url)

            print(f"  - Successfully loaded and processed {len(df)} entries from '{os.path.basename(self.data_path)}'.")
            print("--- Compendium Data Loaded Successfully ---")

        except FileNotFoundError:
            print(f"  - ERROR: '{self.data_path}' not found. Please ensure COMPENDIUM.json is in the correct directory.")
        except Exception as e:
            print(f"  - An unexpected error occurred loading '{self.data_path}': {e}")

    def find_entry(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Finds a single compendium entry by its name (case-insensitive).
        """
        if self.all_entries_df is None:
            return None

        search_query = query.lower().strip()

        exact_match = self.all_entries_df[self.all_entries_df['search_name'] == search_query]
        if not exact_match.empty:
            return exact_match.iloc[0].to_dict()

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

    name = entry.get('name', 'N/A').title()
    category = entry.get('category', 'N/A').title()
    description = entry.get('description', 'No description available.')
    
    response = f"Compendium Entry: {name} (Category: {category})\nDescription: {description}"
    
    locations = entry.get('locations')
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
    
    compendium = CompendiumManager()

    if compendium.all_entries_df is not None:
        # Test searching for an entry to see the new corrected URLs
        query = "bokoblin"
        print(f"\n--- Searching for: '{query}' ---")
        found_entry = compendium.find_entry(query)
        
        if found_entry:
            print("\n--- Raw Entry Data (with corrected URLs) ---")
            print(f"Original Image URL: {found_entry.get('image')}")
            print(f"Corrected Image URL: {found_entry.get('corrected_image_url')}")
            print(f"Original Thumbnail URL: {found_entry.get('thumbnail')}")
            print(f"Corrected Thumbnail URL: {found_entry.get('corrected_thumbnail_url')}")
            
            print("\n--- Formatted Agent Response (Text Only) ---")
            formatted_response = format_entry_for_agent(found_entry)
            print(formatted_response)
        else:
            print(f"Could not find an entry for '{query}'")
    else:
        print("\nTesting aborted as no data was loaded.")
