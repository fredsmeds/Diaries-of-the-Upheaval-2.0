# src/data_management/transcript_manager.py

import os
import re
import time
import xml.etree.ElementTree as ET
import chromadb
import openai
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv()

# --- Initialization ---
try:
    client = OpenAI()
except openai.OpenAIError as e:
    print(f"Error initializing OpenAI client: {e}")
    client = None

# --- Helper Functions ---

def truncate_text(text: str, max_tokens: int = 4000) -> str:
    """Truncates text to a specified maximum number of words."""
    words = text.split()
    if len(words) > max_tokens:
        return " ".join(words[:max_tokens])
    return text

def split_text_into_chunks(text: str, max_words: int = 300, overlap: int = 50) -> list[str]:
    """
    Splits a long text into smaller, overlapping chunks based on word count.
    """
    words = re.split(r'\s+', text)
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = start + max_words
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        
        if end >= len(words):
            break
        start += (max_words - overlap)
        
    return chunks

def get_transcript(video_id: str) -> str | None:
    """
    Fetches the English transcript for a given YouTube video ID.
    *** MODIFIED: Removed the http_client argument for a final test. ***
    """
    try:
        # Calling the library in the simplest possible way.
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-GB'])
        transcript_text = " ".join([item['text'] for item in transcript_list])
        return re.sub(r'\s+', ' ', transcript_text).strip()
    except TranscriptsDisabled:
        print(f"Warning: Transcripts are disabled for video {video_id}. Skipping.")
        return None
    except Exception as e:
        # This will catch the "no element found" error if it still exists.
        print(f"An unexpected error occurred retrieving transcript for video {video_id}: {e}")
        return None

# --- ChromaDB Management Functions ---

def get_chroma_collection(
    collection_name: str = "totk_transcripts",
    db_path: str = "data/chroma_db"
) -> chromadb.Collection | None:
    """
    Initializes a persistent ChromaDB client and returns the specified collection.
    """
    try:
        chroma_client_instance = chromadb.PersistentClient(path=db_path)
        collection = chroma_client_instance.get_or_create_collection(name=collection_name)
        print(f"ChromaDB collection '{collection_name}' accessed/created. Documents: {collection.count()}")
        return collection
    except Exception as e:
        print(f"Error initializing ChromaDB at path '{db_path}': {e}")
        return None

def populate_collection_with_transcripts(
    collection: chromadb.Collection,
    video_ids: list[str]
):
    """
    Fetches transcripts, creates embeddings, and stores them in ChromaDB.
    """
    if not client:
        print("Error: OpenAI client not initialized. Cannot populate database.")
        return

    print(f"\nProcessing {len(video_ids)} videos for embedding...")
    for video_id in video_ids:
        print(f"  - Fetching transcript for video: {video_id}")
        transcript = get_transcript(video_id)
        if not transcript:
            continue

        print(f"  - Splitting transcript into chunks...")
        chunks = split_text_into_chunks(transcript)
        
        if not chunks:
            print(f"  - No chunks generated for video {video_id}. Skipping.")
            continue

        print(f"  - Generating and storing {len(chunks)} embeddings for video {video_id}...")
        for i, chunk in enumerate(chunks):
            chunk_id = f"{video_id}_chunk_{i}"
            
            if collection.get(ids=[chunk_id])['ids']:
                continue

            try:
                embedding_response = client.embeddings.create(
                    input=[chunk],
                    model="text-embedding-ada-002"
                )
                embedding = embedding_response.data[0].embedding

                collection.add(
                    ids=[chunk_id],
                    embeddings=[embedding],
                    documents=[chunk],
                    metadatas=[{'video_id': video_id, 'source_type': 'transcript'}]
                )
            except openai.OpenAIError as e:
                print(f"    - OpenAI API error for chunk {chunk_id}: {e}")
            except Exception as e:
                print(f"    - An unexpected error occurred for chunk {chunk_id}: {e}")
    
    print("\nFinished processing all videos.")
    print(f"Total documents in collection: {collection.count()}")


def get_relevant_context_from_transcripts(
    user_query: str,
    collection: chromadb.Collection,
    n_results_per_query: int = 3,
    max_total_tokens: int = 4000
) -> str:
    """
    Processes a user query to retrieve contextually related information from ChromaDB.
    """
    if not client:
        return "Error: OpenAI client not initialized. Cannot generate embeddings."
    if not collection:
        return "Error: ChromaDB collection not available."

    related_queries = [
        user_query,
        f"Background information on {user_query}",
        f"Historical context of {user_query}",
        f"Key events related to {user_query} in Hyrule's history",
    ]
    
    all_retrieved_texts_set = set()

    for sub_query in related_queries:
        try:
            query_embedding_response = client.embeddings.create(
                input=[sub_query], model="text-embedding-ada-002"
            )
            query_embedding = query_embedding_response.data[0].embedding

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results_per_query,
                include=['documents']
            )

            if results['documents'] and len(results['documents']) > 0:
                for doc in results['documents'][0]:
                    all_retrieved_texts_set.add(doc)
            
            time.sleep(0.1)

        except openai.OpenAIError as e:
            print(f"OpenAI API error for sub-query '{sub_query}': {e}")
            continue
        except Exception as e:
            print(f"Error processing sub-query '{sub_query}': {e}")
            continue

    combined_context = " ".join(list(all_retrieved_texts_set))
    return truncate_text(combined_context, max_tokens=max_total_tokens)


# --- Main Execution Block (for setup and testing) ---
if __name__ == '__main__':
    print("--- Running Transcript Manager for Setup & Testing ---")
    
    video_ids_to_process = [
        'hZytp1sIZAw', 'qP1Fw2EpwqE', 'JuhBs44odO0', 'w31M0LoVUO8',
        'vad1wAe5mB4', 'Q1mRVn0WCrU', 'UhkwrgasKlU',
    ]
    
    lore_collection = get_chroma_collection()

    if lore_collection:
        populate_collection_with_transcripts(
            collection=lore_collection,
            video_ids=video_ids_to_process
        )
        
        print("\n--- Testing Context Retrieval ---")
        test_query = "What is draconification?"
        print(f"Query: '{test_query}'")
        
        context = get_relevant_context_from_transcripts(
            user_query=test_query,
            collection=lore_collection
        )
        
        print("\n--- Retrieved Context ---")
        if context:
            print(context[:500] + "...")
            print(f"\nContext length: {len(context.split())} words")
        else:
            print("No context was retrieved.")
    else:
        print("Could not initialize ChromaDB collection. Process aborted.")
