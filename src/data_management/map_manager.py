# src/data_management/map_manager.py

import os
import json
from PIL import Image
import glob
import logging

# --- Configuration ---
logging.basicConfig(level=logging.INFO)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
DATA_DIR = os.path.join(BASE_DIR, 'data')
ICON_DIR = os.path.join(ASSETS_DIR, 'icons')
MAP_DATA_DIR = os.path.join(DATA_DIR, 'maps', 'source_json') 
GENERATED_MAPS_DIR = os.path.join(BASE_DIR, 'generated_maps')
os.makedirs(GENERATED_MAPS_DIR, exist_ok=True)

# --- Constants ---
MAP_SCALE = 3.5
MAP_OFFSET_X = 10500
MAP_OFFSET_Z = 10500
CANVAS_WIDTH = 6000
CANVAS_HEIGHT = 6000

class MapManager:
    def __init__(self):
        """
        Initializes the MapManager by loading all map location data from the JSON files.
        """
        logging.info("--- Initializing MapManager (v3 - Final) ---")
        self.locations = self._load_all_locations()
        self.icons = self._load_icon_paths()

    def _load_all_locations(self):
        all_locations = {"surface": {}, "sky": {}, "depths": {}}
        if not os.path.exists(MAP_DATA_DIR):
            logging.error(f"FATAL: Map data directory not found at: {MAP_DATA_DIR}")
            return all_locations

        json_files = glob.glob(os.path.join(MAP_DATA_DIR, '**', '*.json'), recursive=True)
        if not json_files:
            logging.warning(f"No map marker JSON files found in {MAP_DATA_DIR}.")
            return all_locations

        for file_path in json_files:
            try:
                layer = "surface"
                if "sky" in file_path.lower(): layer = "sky"
                elif "depths" in file_path.lower(): layer = "depths"
                category = os.path.splitext(os.path.basename(file_path))[0]

                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                locations_list = data if isinstance(data, list) else next(iter(data.values()), [])
                
                if not isinstance(locations_list, list): continue

                if category not in all_locations[layer]: all_locations[layer][category] = []
                
                for loc in locations_list:
                    if isinstance(loc, dict): loc['category'] = category
                
                all_locations[layer][category].extend(locations_list)
            except Exception as e:
                logging.error(f"Error processing file {file_path}: {e}")
        return all_locations

    def _load_icon_paths(self):
        icons = {}
        if not os.path.exists(ICON_DIR): return icons
        for icon_file in os.listdir(ICON_DIR):
            if icon_file.endswith('.png'):
                icon_name = os.path.splitext(icon_file)[0]
                icons[icon_name] = os.path.join(ICON_DIR, icon_file)
        logging.info(f"Loaded {len(icons)} icon paths.")
        return icons

    def _translate_coords_to_pixels(self, game_x, game_z):
        pixel_x = (game_x + MAP_OFFSET_X) / MAP_SCALE
        pixel_y = (game_z + MAP_OFFSET_Z) / MAP_SCALE
        return int(pixel_x), int(pixel_y)

    def find_locations_by_category(self, category, layer="surface"):
        """Finds all locations of a specific category."""
        logging.info(f"Searching for category '{category}' on layer '{layer}'...")
        return self.locations.get(layer, {}).get(category, [])

    def find_locations_by_specific_name(self, category, name, layer="surface"):
        """Finds all locations of a specific item within a category."""
        logging.info(f"Searching for specific item '{name}' in category '{category}' on layer '{layer}'...")
        category_locations = self.find_locations_by_category(category, layer)
        return [loc for loc in category_locations if name.lower() in loc.get('name', '').lower()]

    def generate_map_image(self, locations_to_mark, layer="surface", output_filename="generated_map.png"):
        if not locations_to_mark:
            logging.warning("generate_map_image called with no locations to mark.")
            return None
        try:
            map_image = Image.new('RGBA', (CANVAS_WIDTH, CANVAS_HEIGHT), (12, 16, 33, 255))
            for location in locations_to_mark:
                category = location.get("category")
                if not category: continue

                icon_path = self.icons.get(category)
                if not icon_path:
                    singular_category = category[:-1] if category.endswith('s') else None
                    if singular_category: icon_path = self.icons.get(singular_category)
                if not icon_path: continue

                icon_image = Image.open(icon_path).convert("RGBA")
                icon_size = (60, 60)
                icon_image = icon_image.resize(icon_size, Image.Resampling.LANCZOS)
                
                game_x, game_z = location.get('x'), location.get('z')
                if game_x is None or game_z is None: continue

                pixel_x, pixel_y = self._translate_coords_to_pixels(float(game_x), float(game_z))
                paste_x, paste_y = pixel_x - (icon_image.width // 2), pixel_y - (icon_image.height // 2)
                map_image.paste(icon_image, (paste_x, paste_y), icon_image)
            
            output_path = os.path.join(GENERATED_MAPS_DIR, output_filename)
            map_image.save(output_path, "PNG")
            logging.info(f"Successfully generated map image and saved to {output_path}")
            return output_path
        except Exception as e:
            logging.error(f"Failed to generate map image: {e}", exc_info=True)
            return None
