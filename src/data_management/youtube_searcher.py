# src/data_management/youtube_searcher.py

import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import List, Dict, Any

# --- Configuration ---
# We no longer define the API key here at the module level.
# YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY") # This was the problem line
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

def search_youtube_for_walkthrough(query: str, max_results: int = 3) -> str:
    """
    Searches YouTube for walkthrough videos related to a specific query and returns
    a formatted string with the top results.

    Args:
        query: The search term (e.g., "Rotsumamu Shrine", "Colgera boss fight").
        max_results: The maximum number of video links to return.

    Returns:
        A formatted string with video titles and links, or an error/not found message.
    """
    # *** FIX: Get the API key from the environment inside the function. ***
    # This ensures it's fetched *after* load_dotenv() has been called.
    api_key = os.getenv("YOUTUBE_API_KEY")
    
    if not api_key:
        return "I am sorry, but I cannot search for guidance at this time. The connection to the archives is unavailable."

    try:
        # Build the YouTube API service object
        youtube = build(
            YOUTUBE_API_SERVICE_NAME,
            YOUTUBE_API_VERSION,
            developerKey=api_key # Use the key we just fetched
        )

        # Construct a search query focused on Tears of the Kingdom walkthroughs
        search_query = f"Tears of the Kingdom {query} walkthrough guide"

        # Call the search.list method to retrieve results
        search_response = youtube.search().list(
            q=search_query,
            part="snippet",
            maxResults=max_results,
            type="video"  # We only want video results
        ).execute()

        videos = search_response.get("items", [])

        if not videos:
            return f"I searched the archives but could not find specific guidance for '{query}'."

        # Format the results into a clean string for the agent
        formatted_results = ["Here are some visual records that may aid you on your quest:"]
        for item in videos:
            title = item["snippet"]["title"]
            video_id = item["id"]["videoId"]
            link = f"https://www.youtube.com/watch?v={video_id}"
            formatted_results.append(f"- {title}: {link}")
        
        return "\n".join(formatted_results)

    except HttpError as e:
        print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
        return "An error occurred while searching the archives. Please try again later."
    except Exception as e:
        print(f"An unexpected error occurred during YouTube search: {e}")
        return "An unexpected error occurred while searching the archives."

# --- Main Execution Block (for setup and testing) ---
if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    
    print("--- Testing YouTube Searcher ---")
    
    if not os.getenv("YOUTUBE_API_KEY"):
        print("\nERROR: YOUTUBE_API_KEY not found in environment variables.")
        print("Please check that your .env file is in the project root and contains the correct key.")
    else:
        print("YouTube API Key found. Proceeding with tests...")
        
        test_query = "Rotsumamu Shrine"
        print(f"\nSearching for: '{test_query}'")
        
        results = search_youtube_for_walkthrough(test_query)
        
        print("\n--- Search Results ---")
        print(results)
        
        print("\n--- Testing with a different query ---")
        test_query_2 = "Colgera boss fight"
        print(f"\nSearching for: '{test_query_2}'")
        
        results_2 = search_youtube_for_walkthrough(test_query_2)
        
        print("\n--- Search Results ---")
        print(results_2)
