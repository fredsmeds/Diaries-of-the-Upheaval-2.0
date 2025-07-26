# src/data_management/map_manager.py

import os
import json
import tempfile
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw

class MapManager:
    """
    Manages loading map data, searching for locations, and generating custom map images.
    """
    def __init__(self, 
                 data_path: str = "data/maps/markers", 
                 map_image_path: str = "assets/maps", 
                 icon_path: str = "assets/icons"):
        print("--- Initializing Map Manager ---")
        self.data_path = data_path
        self.map_image_path = map_image_path
        self.icon_path = icon_path
        self.region_bounds = {
            "lanayru": {"x_min": 2800, "x_max": 4700, "y_min": -1200, "y_max": 1500, "layer": "surface"},
            "central hyrule": {"x_min": -1500, "x_max": 1500, "y_min": -1500, "y_max": 1500, "layer": "surface"},
            "hyrule castle": {"x_min": -500, "x_max": 200, "y_min": 500, "y_max": 1300, "layer": "surface"},
            "hebra": {"x_min": -4500, "x_max": -1500, "y_min": 1500, "y_max": 4000, "layer": "surface"},
            "gerudo": {"x_min": -4800, "x_max": -1800, "y_min": -3800, "y_max": -1500, "layer": "surface"},
            "faron": {"x_min": 0, "x_max": 3000, "y_min": -4000, "y_max": -2000, "layer": "surface"},
            "necluda": {"x_min": 1500, "x_max": 4000, "y_min": -3000, "y_max": -1000, "layer": "surface"},
            "akkala": {"x_min": 3000, "x_max": 4800, "y_min": 1500, "y_max": 4000, "layer": "surface"},
            "eldin": {"x_min": 1000, "x_max": 3000, "y_min": 1500, "y_max": 4000, "layer": "surface"},
        }
        self.locations_db = self._load_all_locations()
        if self.locations_db:
            print(f"--- Map Manager Initialized: Loaded {len(self.locations_db)} total locations. ---")

    def _load_all_locations(self) -> List[Dict[str, Any]]:
        all_locations = []
        layers = ["surface", "sky", "depths"]
        for layer in layers:
            layer_path = os.path.join(self.data_path, layer)
            if not os.path.isdir(layer_path): continue
            
            for filename in os.listdir(layer_path):
                if filename.endswith(".json"):
                    file_path = os.path.join(layer_path, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for category_data in data:
                            category_name = category_data.get("name", "Unknown")
                            for layer_info in category_data.get("layers", []):
                                icon_url = layer_info.get("icon", {}).get("url", "default.png")
                                for marker in layer_info.get("markers", []):
                                    all_locations.append({
                                        "name": marker.get("name"),
                                        "category": category_name,
                                        "layer": layer,
                                        "coords": marker.get("coords"),
                                        "icon": icon_url,
                                    })
        return all_locations

    def find_single_location(self, name: str) -> Optional[Dict[str, Any]]:
        """Finds a single, specific location by its name, prioritizing exact matches."""
        search_name = name.lower().strip()
        # Prioritize exact matches
        for loc in self.locations_db:
            if loc["name"] and loc["name"].lower() == search_name:
                return loc
        # Fallback to partial match if no exact match is found
        for loc in self.locations_db:
            if loc["name"] and search_name in loc["name"].lower():
                return loc
        print(f"--> Single location not found for name: '{name}'")
        return None

    def find_locations_in_region(self, category: str, region: str) -> List[Dict[str, Any]]:
        """Finds all locations of a given category within a defined region."""
        search_category = category.lower().strip().replace(' ', '').replace('s', '')
        search_region = region.lower().strip()

        bounds = self.region_bounds.get(search_region)
        if not bounds:
            print(f"Region '{region}' not defined in map_manager.")
            return []

        found_locations = []
        for loc in self.locations_db:
            loc_category = loc["category"].lower().strip().replace(' ', '').replace('s', '')
            if search_category in loc_category and loc["layer"] == bounds["layer"]:
                coords = loc.get("coords")
                if coords and (bounds["x_min"] <= coords[0] <= bounds["x_max"]) and (bounds["y_min"] <= coords[1] <= bounds["y_max"]):
                    found_locations.append(loc)
        
        print(f"--> Found {len(found_locations)} '{category}' locations in '{region}'.")
        return found_locations

    def generate_map_image(self, locations: List[Dict[str, Any]]) -> Optional[str]:
        """Dynamically creates a new map image by pasting icons onto a base map."""
        if not locations:
            return None

        layer = locations[0]['layer']
        base_map_name = f"{layer}.jpg"
        base_map_path = os.path.join(self.map_image_path, base_map_name)

        if not os.path.exists(base_map_path):
            print(f"ERROR: Base map not found at {base_map_path}")
            return None

        base_map = Image.open(base_map_path).convert("RGBA")
        
        # Create a transparent overlay for drawing icons
        overlay = Image.new("RGBA", base_map.size, (255, 255, 255, 0))

        # Game coordinate range to pixel range mapping
        map_width, map_height = base_map.size
        game_x_range = (-6000, 6000)
        game_y_range = (-4000, 4000)

        def translate_coords(game_x, game_y):
            pixel_x = int(((game_x - game_x_range[0]) / (game_x_range[1] - game_x_range[0])) * map_width)
            pixel_y = int(((game_y_range[1] - game_y) / (game_y_range[1] - game_y_range[0])) * map_height)
            return pixel_x, pixel_y

        for loc in locations:
            icon_filename = os.path.basename(loc['icon'])
            icon_path = os.path.join(self.icon_path, icon_filename)
            
            if os.path.exists(icon_path):
                try:
                    icon = Image.open(icon_path).convert("RGBA")
                    # Standardize icon size
                    icon_size = 32
                    icon = icon.resize((icon_size, icon_size)) 
                    coords = loc.get("coords")
                    if coords:
                        px, py = translate_coords(coords[0], coords[1])
                        # Paste the icon onto the transparent overlay
                        overlay.paste(icon, (px - icon_size//2, py - icon_size//2), icon)
                except Exception as e:
                    print(f"Could not process icon {loc['icon']}: {e}")

        # Combine the base map and the icon overlay
        combined_image = Image.alpha_composite(base_map, overlay)

        # Save the final image to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png", mode='wb') as temp_file:
            combined_image.save(temp_file, format='PNG')
            print(f"--> Generated custom map at: {temp_file.name}")
            return temp_file.name

        return None