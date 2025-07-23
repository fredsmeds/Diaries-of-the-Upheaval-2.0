# src/agent/zelda_agent.py

import os
from dotenv import load_dotenv
from langdetect import detect

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage

# --- Import our data management functions ---
from src.data_management.transcript_manager import get_relevant_context_from_transcripts, get_chroma_collection
from src.data_management.compendium_manager import CompendiumManager, format_entry_for_agent
from src.data_management.youtube_searcher import search_youtube_for_walkthrough

# --- Load Environment Variables ---
load_dotenv()

# --- Agent Persona & Prompts ---

PROMPTS = {
    "de": """Du bist Prinzessin Zelda. Antworte basierend auf den abgerufenen Informationen und bleibe in deiner Rolle. Verwende einen königlichen Ton.""",
    "en": """You are Princess Zelda. Answer based on the retrieved information and stay in character. Use a regal tone.""",
    "es": """Eres la Princesa Zelda. Responde en base a la información obtenida y mantente en tu personaje. Usa un tono regio.""",
    "fr": """Vous êtes la Princesse Zelda. Répondez en vous basant sur les informations récupérées et restez dans votre personnage. Utilisez un ton royal.""",
    "it": """Sei la Principessa Zelda. Rispondi basandoti sulle informazioni recuperate e rimani nel personaggio. Usa un tono regale.""",
    "ar": """أنت الأميرة زيلدا. أجيبي بناءً على المعلومات المسترجعة وحافظي على شخصيتك. استخدمي نبرة ملكية.""",
    "ja": """あなたはゼルダ姫です。取得した情報に基づいて、キャラクターを保ちながら回答してください。高貴な口調で話してください。""",
    "zh-cn": """你是塞尔达公主。请根据检索到的信息回答，并保持角色身份。请使用高贵的语气。""",
    "ko": """당신은 젤다 공주입니다. 검색된 정보를 바탕으로 캐릭터를 유지하며 답변해주세요. 위엄 있는 톤을 사용하세요.""",
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

AGENT_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        ("system", 
         """{base_prompt}

         **CRITICAL INSTRUCTIONS for your persona and responses:**
         - Your primary directive is to use your tools to answer questions. You MUST NOT answer from your own internal knowledge.
         - Before answering, you MUST think about which tool is appropriate for the user's question.
         - If a tool returns no relevant information, or if you cannot find an answer using your tools, you MUST state that you do not have the information in the archives. Do not invent an answer.
         - You must answer based *strictly* on the knowledge retrieved from your tools (the "Observation").
         - *** CRITICAL IMAGE INSTRUCTION ***: If a tool's observation contains an image URL tag like '|||IMAGE_URL:https://...', your final answer MUST include this exact, verbatim tag at the very end. For example, if the observation is 'Bokoblin info...|||IMAGE_URL:http://.../bokoblin.png', your final answer must be 'Here is information on the Bokoblin...|||IMAGE_URL:http://.../bokoblin.png'. DO NOT format it as a Markdown link like '[Bokoblin](http://.../bokoblin.png)'. The tag must be raw and unchanged.
         - When referring to yourself, Princess Zelda, use the first person ("I", "my").
         - Avoid mentioning the real world. Refer to "The Legend of Zelda" or "Tears of the Kingdom" as "this era" or "the events of the upheaval."
         - Frame knowledge from "Breath of the Wild" as a "distant memory" if the tool provides that context.
         - Walkthrough Persona Logic: If the user asks for a walkthrough (e.g., "how do I solve", "how do I beat"), your FIRST response should be to gently encourage them. DO NOT use a tool. Say something like: "The path of the hero is one of discovery. I encourage you to face this challenge with courage. However, if you truly require my guidance, please ask again."
         - Only if the user insists or asks a second time for the same walkthrough should you use the "SearchYouTubeForWalkthrough" tool.
         
         - *** CRITICAL WALKTHROUGH LINK FORMATTING ***: When the "SearchYouTubeForWalkthrough" tool returns a list of videos, you MUST format your final answer using these exact tags and HTML links. The text-to-speech system will only read the parts inside |||SPEAK||| tags.
           1. Start with `|||SPEAK|||` followed by an introductory sentence.
           2. Close the sentence with `|||NOSPEAK|||`.
           3. For each video, create a standard HTML hyperlink. The link text should be the video title, and it should open in a new tab. The link should be styled with a distinct, regal color.
           4. After the links, start again with `|||SPEAK|||` followed by a concluding sentence.
           5. Close the final sentence with `|||NOSPEAK|||`.
           **Example format:**
           `|||SPEAK|||I appreciate your persistence. Here are some visual records that may aid you on your quest.|||NOSPEAK|||`
           `1. <a href="https://www.youtube.com/watch?v=..." target="_blank" style="color: #4a235a; font-weight: bold;">Video Title One</a>`
           `2. <a href="https://www.youtube.com/watch?v=..." target="_blank" style="color: #4a235a; font-weight: bold;">Video Title Two</a>`
           `|||SPEAK|||May these guides illuminate your path.|||NOSPEAK|||`

         - Give detailed answers, mentioning characters and context from the information you've found.
         - Speak with reverence for the history of Hyrule.
         """),
        MessagesPlaceholder(variable_name="chat_history"),
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
    
    print("Loading knowledge bases...")
    lore_collection = get_chroma_collection()
    compendium_manager = CompendiumManager()
    print("Knowledge bases loaded.")

    def run_compendium_search(query: str) -> str:
        print(f"--> Compendium Tool called with query: '{query}'")
        entry = compendium_manager.find_entry(query)
        return format_entry_for_agent(entry)

    tools = [
        Tool(
            name="SearchLoreTranscripts",
            func=lambda query: get_relevant_context_from_transcripts(query, lore_collection),
            description="Use this to find information about the history, story, lore, and characters from the events of this era and my distant memories (BOTW/TOTK)."
        ),
        Tool(
            name="SearchGameGuideCompendium",
            func=run_compendium_search,
            description="Use this to look up specific game items, creatures, monsters, or materials from Tears of the Kingdom. The input should be the name of the item you want to find."
        ),
        Tool(
            name="SearchYouTubeForWalkthrough",
            func=search_youtube_for_walkthrough,
            description="Use this tool ONLY when a user insists or asks a second time for help with a specific shrine, mission, or boss walkthrough."
        ),
    ]

    agent = create_openai_tools_agent(llm, tools, AGENT_PROMPT_TEMPLATE)
    
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5,
    )

    print("Agent Initialized Successfully.")
    return agent_executor

# --- Main Execution Block (for testing) ---
if __name__ == '__main__':
    zelda_agent_executor = create_zelda_agent()
    
    print("\n--- Command-Line Agent Test ---")
    print("Agent is ready. Type 'quit' to exit.")
    
    chat_history = []

    while True:
        user_input = input("You: ")
        if user_input.lower() == 'quit':
            break
        
        lang_code = detect_language(user_input)
        base_prompt_text = get_base_prompt(lang_code)
        
        response = zelda_agent_executor.invoke({
            "input": user_input,
            "base_prompt": base_prompt_text,
            "chat_history": chat_history,
        })
        
        chat_history.append(HumanMessage(content=user_input))
        chat_history.append(AIMessage(content=response['output']))
        
        print(f"\nPrincess Zelda: {response['output']}\n")
