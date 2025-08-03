# src/data_management/web_scraper.py

import requests
from bs4 import BeautifulSoup
import logging
import json
from googlesearch import search

# --- Configuration ---
logging.basicConfig(level=logging.INFO)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def find_ign_url_with_google(query: str) -> str | None:
    """
    Uses Google to find the most relevant IGN guide page for a query.
    This is more robust than relying on IGN's internal search.
    """
    try:
        search_query = f"site:ign.com {query} Tears of the Kingdom"
        logging.info(f"Performing Google search for: '{search_query}'")
        
        # Use the 'googlesearch-python' library to find the top result
        search_results = list(search(search_query, num=1, stop=1, pause=2))
        
        if search_results:
            url = search_results[0]
            logging.info(f"Found IGN URL via Google: {url}")
            return url
        else:
            logging.warning(f"Google search found no relevant IGN URL for '{query}'")
            return None
            
    except Exception as e:
        logging.error(f"An error occurred during Google search for IGN URL: {e}")
        return None

def scrape_ign_page_for_data(url: str) -> dict:
    """
    Scrapes a given IGN wiki page for a summary paragraph and the main image URL.
    """
    if not url:
        return {"summary": None, "image_url": None}
        
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        summary = None
        image_url = None

        # --- Find Summary ---
        # Find the main content area of the wiki
        main_content = soup.find('div', class_='prose')
        if main_content:
            # Find the first paragraph that is a direct child of the main content
            first_paragraph = main_content.find('p', recursive=False)
            if first_paragraph:
                summary = first_paragraph.get_text(strip=True)

        # --- Find Image ---
        # The main image is often in a 'figure' element within the main content
        if main_content:
            img_tag = main_content.find('img')
            if img_tag and img_tag.has_attr('src'):
                image_url = img_tag['src']

        logging.info(f"Scraped data: Summary found ({summary is not None}), Image found ({image_url is not None})")
        return {"summary": summary, "image_url": image_url}

    except requests.exceptions.RequestException as e:
        logging.error(f"Error scraping IGN page {url}: {e}")
        return {"summary": None, "image_url": None}

def get_ign_data_for_agent(query: str) -> str:
    """
    A wrapper function for the agent. It searches for and scrapes an IGN page,
    then formats the output as a string for the agent to use.
    """
    page_url = find_ign_url_with_google(query)
    if not page_url:
        return f"I could not find a relevant guide page on the IGN wiki for '{query}'."
        
    scraped_data = scrape_ign_page_for_data(page_url)
    
    summary = scraped_data.get('summary')
    image_url = scraped_data.get('image_url')

    if not summary and not image_url:
        return "I found a page, but I was unable to extract a clear summary or image."
    
    # Format the response for the agent, including our special image tag if found.
    response_parts = []
    if summary:
        response_parts.append(summary)
    if image_url:
        # Prepend our special tag
        response_parts.append(f"|||IMAGE_URL:{image_url}|||")
        
    return "\n".join(response_parts)
