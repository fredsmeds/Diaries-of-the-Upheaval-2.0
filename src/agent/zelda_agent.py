# src/agent/zelda_agent.py

import os
from dotenv import load_dotenv
from langdetect import detect

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
from langchain.memory import ConversationBufferMemory

# Import our data management functions
from src.data_management.transcript_manager import get_relevant_context_from_transcripts, get_chroma_collection

# --- Load Environment Variables ---
load_dotenv()

# --- Agent Persona & Prompts ---

PROMPTS = {
    "de": """Du bist Prinzessin Zelda. Antworte basierend auf den abgerufenen Informationen und bleibe in deiner Rolle. Verwende einen königlichen Ton.""",
    "en": """You are Princess Zelda. Answer based on the retrieved information and stay in character. Use a regal tone.""",
    "es": """Eres la Princesa Zelda. Responde en base a la información obtenida y mantente en tu personaje. Usa un tono regio.""",
}

def detect_language(text: str) -> str:
    """Detects the language of the input text."""
    try:
        return detect(text)
    except:
        return "en"

def get_base_prompt(language_code: str) -> str:
    """Gets the base persona prompt for a given language."""
    return PROMPTS.get(language_code, PROMPTS["en"])

# *** NEW: Simplified Prompt for Tool-Calling Agent ***
# The complex ReAct formatting is no longer needed. We create a chat-style prompt.
AGENT_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        ("system", 
         """{base_prompt}

         **CRITICAL INSTRUCTIONS for your persona and responses:**
         - You must answer based *strictly* on the knowledge retrieved from your tools. Do not use any external knowledge.
         - When referring to yourself, Princess Zelda, use the first person ("I", "my").
         - Avoid mentioning the real world. Refer to "The Legend of Zelda" or "Tears of the Kingdom" as "this era" or "the events of the upheaval."
         - Frame knowledge from "Breath of the Wild" as a "distant memory" if the tool provides that context.
         - For walkthrough questions ("how do I solve..."), your first response should be to gently encourage the user. Only if they insist should you use the tool to find a video link.
         - Give detailed answers, mentioning characters and context from the information you've found.
         - Speak with reverence for the history of Hyrule.
         """),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)


# --- Agent Initialization ---

def create_zelda_agent():
    """
    Creates and initializes the LangChain agent for Princess Zelda.
    """
    print("Initializing Princess Zelda Agent...")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    lore_collection = get_chroma_collection()

    tools = [
        Tool(
            name="SearchLoreTranscripts",
            func=lambda query: get_relevant_context_from_transcripts(query, lore_collection),
            description="Use this to find information about the history, story, lore, and characters from the events of this era and my distant memories (BOTW/TOTK)."
        ),
        Tool(
            name="SearchGameGuideCompendium",
            func=lambda query: "This information is not in my current knowledge. I can only speak to the lore and history I have access to.",
            description="Use this to look up specific game items, creatures, monsters, or materials from Tears of the Kingdom."
        ),
        Tool(
            name="SearchYouTubeForWalkthrough",
            func=lambda query: "I cannot provide a direct link, but I encourage you to seek out moving pictures of other adventurers on the platform known as YouTube for guidance on this quest.",
            description="Use this ONLY when a user insists on getting help for a specific shrine or mission walkthrough."
        ),
    ]

    # *** NEW: Use create_openai_tools_agent for a more reliable agent ***
    agent = create_openai_tools_agent(llm, tools, AGENT_PROMPT_TEMPLATE)
    
    # Re-enable memory, as tool-calling agents handle it better.
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory, 
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5,
    )

    print("Agent Initialized Successfully.")
    return agent_executor

# --- Main Execution Block (for testing) ---
if __name__ == '__main__':
    zelda_agent_executor = create_zelda_agent()
    
    print("\n--- Testing Agent ---")
    print("Agent is ready. Type 'quit' to exit.")
    
    # We need to maintain the chat history for the test loop
    chat_history = []

    while True:
        user_input = input("You: ")
        if user_input.lower() == 'quit':
            break
        
        lang_code = detect_language(user_input)
        base_prompt_text = get_base_prompt(lang_code)
        
        # *** MODIFIED: The invoke call is now simpler ***
        response = zelda_agent_executor.invoke({
            "input": user_input,
            "base_prompt": base_prompt_text,
            "chat_history": chat_history,
        })
        
        # Update the history with the latest interaction
        chat_history.extend(response['chat_history'])
        
        print(f"\nPrincess Zelda: {response['output']}\n")
