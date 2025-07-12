# src/data_management/transcript_manager.py

import os
import time
import chromadb
import openai
from openai import OpenAI

# --- Initialization ---
# It's good practice to initialize the client once. This code assumes that
# load_dotenv() has been called elsewhere (e.g., in app.py or a config module)
# so that os.getenv() can access the API key.
try:
    # This uses the OPENAI_API_KEY environment variable by default.
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

# --- ChromaDB Management Functions ---

def get_chroma_collection(
    collection_name: str = "totk_transcripts",
    db_path: str = "data/chroma_db"  # Specify a path for persistent storage
) -> chromadb.Collection | None:
    """
    Initializes a persistent ChromaDB client and returns the specified collection.
    
    Args:
        collection_name: The name of the collection to get or create.
        db_path: The directory path to store the database files.

    Returns:
        A ChromaDB Collection object, or None if an error occurs.
    """
    try:
        # Using PersistentClient to save the database to disk
        chroma_client_instance = chromadb.PersistentClient(path=db_path)
        collection = chroma_client_instance.get_or_create_collection(name=collection_name)
        print(f"ChromaDB collection '{collection_name}' accessed/created. Documents: {collection.count()}")
        return collection
    except Exception as e:
        print(f"Error initializing ChromaDB at path '{db_path}': {e}")
        return None


def get_relevant_context_from_transcripts(
    user_query: str,
    collection: chromadb.Collection,
    n_results_per_query: int = 3,
    max_total_tokens: int = 4000
) -> str:
    """
    Processes a user query to retrieve contextually related information from ChromaDB
    using optimized querying and modern OpenAI v1.x embeddings.

    This function replaces the old, inefficient `multi_query_processing`.

    Args:
        user_query: The user's original question.
        collection: The ChromaDB collection object to query.
        n_results_per_query: The number of results to fetch for each sub-query.
        max_total_tokens: The maximum number of tokens for the final context string.

    Returns:
        A single string containing the combined, relevant context.
    """
    if not client:
        return "Error: OpenAI client not initialized. Cannot generate embeddings."
    if not collection:
        return "Error: ChromaDB collection not available."

    # The multi-query expansion strategy is preserved to get rich context
    related_queries = [
        user_query,
        f"Background information on {user_query}",
        f"Historical context of {user_query}",
        f"Key events related to {user_query} in Hyrule's history",
    ]
    
    # Use a set to automatically handle duplicate chunks of text
    all_retrieved_texts_set = set()

    for sub_query in related_queries:
        try:
            # 1. Refactored OpenAI Embedding Call (v1.x syntax)
            query_embedding_response = client.embeddings.create(
                input=[sub_query],
                model="text-embedding-ada-002"
            )
            query_embedding = query_embedding_response.data[0].embedding

            # 2. OPTIMIZED ChromaDB Query
            # This is the core improvement. We use collection.query() to let ChromaDB
            # perform the efficient similarity search on the server/file side.
            # We no longer fetch the entire database with collection.get().
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results_per_query,
                include=['documents']  # We only need the document text for the context
            )

            # 3. Extract the document texts from the results
            if results['documents'] and len(results['documents']) > 0:
                # results['documents'] is a list containing one list of results
                for doc in results['documents'][0]:
                    all_retrieved_texts_set.add(doc)
            
            # A small delay can be polite to APIs, but may not be strictly necessary here
            time.sleep(0.1)

        except openai.OpenAIError as e:
            print(f"OpenAI API error during embedding for sub-query '{sub_query}': {e}")
            continue  # Skip this sub-query on error
        except Exception as e:
            print(f"Error processing sub-query '{sub_query}': {e}")
            continue

    # 4. Combine unique texts and truncate to the desired length
    combined_context = " ".join(list(all_retrieved_texts_set))
    
    return truncate_text(combined_context, max_tokens=max_total_tokens)

# --- Example Usage (for testing this module directly) ---
if __name__ == '__main__':
    # This block will only run when you execute this file directly
    # e.g., `python src/data_management/transcript_manager.py`
    
    # You would need to make sure your .env file is loaded.
    # For direct testing, you might add:
    from dotenv import load_dotenv
    load_dotenv()

    print("--- Testing ChromaDB Manager ---")
    
    # Step 1: Get the collection
    # Note: You need to have data IN the collection for queries to work.
    # You would first run a script to populate it with transcript embeddings.
    lore_collection = get_chroma_collection()

    if lore_collection:
        # Step 2: Test the context retrieval function
        test_query = "What happened to the Zonai?"
        print(f"\nTesting with query: '{test_query}'")
        
        context = get_relevant_context_from_transcripts(
            user_query=test_query,
            collection=lore_collection
        )
        
        print("\n--- Retrieved Context ---")
        if context:
            print(context)
            print(f"\nContext length: {len(context.split())} words")
        else:
            print("No context was retrieved. Is the database populated?")
    else:
        print("Could not initialize ChromaDB collection. Test aborted.")
