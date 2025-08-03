# src/agent/zelda_agent.py

import os
import logging
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
from langchain.memory import ConversationBufferMemory

# --- Import Project-Specific Modules ---
from src.data_management.transcript_manager import get_relevant_context_from_transcripts
from src.data_management.compendium_manager import CompendiumManager, format_entry_for_agent
from src.data_management.youtube_searcher import search_youtube_for_walkthrough
from src.data_management.map_manager import MapManager
from src.data_management.web_scraper import get_ign_data_for_agent

# --- Initialize Managers & LLM ---
compendium_manager = CompendiumManager()
map_manager = MapManager()
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# --- Multilingual Prompts ---
PROMPTS = {
    'en': "You are Princess Zelda. Your tone is regal, wise, and encouraging. Answer based on the retrieved information and stay in character.",
    'de': "Du bist Prinzessin Zelda. Dein Ton ist königlich, weise und ermutigend. Antworte basierend auf den abgerufenen Informationen und bleibe in deiner Rolle.",
    'es': "Eres la Princesa Zelda. Tu tono es regio, sabio y alentador. Responde en base a la información obtenida y mantente en tu personaje.",
    'fr': "Vous êtes la Princesse Zelda. Votre ton est royal, sage et encourageant. Répondez en vous basant sur les informations récupérées et restez dans votre personnage.",
    'it': "Sei la Principessa Zelda. Il tuo tono è regale, saggio e incoraggiante. Rispondi basandoti sulle informazioni recuperate e rimani nel personaggio.",
    'pt': "Você é a Princesa Zelda. Seu tom é real, sábio e encorajador. Responda com base nas informações recuperadas e permaneça no personagem.",
    'ar': "أنت الأميرة زيلدا. لهجتك ملكية وحكيمة ومشجعة. أجيبي بناءً على المعلومات المسترجعة وحافظي على شخصيتك.",
    'ja': "あなたはゼルダ姫です。あなたの口調は気高く、賢く、励ますようです。取得した情報に基づいて、キャラクターを保ちながら回答してください。",
    'zh-cn': "你是塞尔达公主。你的语气高贵、睿智、鼓舞人心。请根据检索到的信息回答，并保持角色身份。",
    'ko': "당신은 젤다 공주입니다. 당신의 어조는 고귀하고, 현명하며, 격려적입니다. 검색된 정보를 바탕으로 캐릭터를 유지하며 답변해주세요。",
}

# --- Detailed System Prompt Template ---
SYSTEM_PROMPT_TEMPLATE = """
{base_prompt}

**CRITICAL INSTRUCTIONS:**
- You MUST use your tools to answer questions. Do not answer from your own knowledge.
- You must answer based *strictly* on the knowledge retrieved from your tools.

**TOOL USAGE LOGIC:**
- **Lore:** For history, story, characters, use 'SearchLoreTranscripts'.
- **Images/Descriptions:** For a "picture of" or info on a creature/item, **use `SearchIgnWiki` FIRST**. Use `SearchTotkCompendium` as a backup.
- **Walkthroughs:** For walkthroughs, encourage first. If they insist, use 'SearchYouTubeForWalkthrough'.
- **Maps & Locations:** For queries like "where are the koroks" or "show me a map of shrines", you MUST follow this order:
    1.  **ALWAYS try the `GenerateMap` tool FIRST.**
    2.  If the `GenerateMap` tool returns a message like "I could not find any locations...", then you should **immediately try the `SearchIgnWiki` tool** with the same query (e.g., "koroks in eldin") as a backup.

**MAP TOOL INSTRUCTIONS (VERY IMPORTANT):**
The `GenerateMap` tool requires a `category` and an optional `specific_item`.
- The `category` MUST be one of the following exact strings: 'caves', 'chests', 'creatures', 'dispensers', 'koroks', 'labels', 'locations', 'materials', 'monsters', 'othermarkers', 'quests', 'services', 'tgates', 'treasure'.
- From the user's query, you must determine the correct category.
- **Example 1:** If the user asks "show me the shrines", you must recognize that "shrines" are a type of "tgates". You will call the tool with `category='tgates'`.
- **Example 2:** If the user asks "where are the ice chuchus", you must recognize that "ice chuchus" are a type of "monster". You will call the tool with `category='monsters'` and `specific_item='ice chuchu'`.

**FORMATTING RULES:**
- **Images:** The response MUST contain `|||IMAGE_URL:...|||` on a new line.
- **Maps:** The response MUST contain `|||MAP_URL:generated_maps/...|||` on a new line.

{language_instruction}
"""

def generate_map_wrapper(category: str, specific_item: str = None, layer: str = "surface"):
    """Wrapper for the map generation tool to handle different query types."""
    logging.info(f"--> Map Tool called with Category: '{category}', Specific Item: '{specific_item}'")
    locations = []
    if specific_item:
        locations = map_manager.find_locations_by_specific_name(category, specific_item, layer)
    else:
        locations = map_manager.find_locations_by_category(category, layer)
    
    if not locations:
        return "I could not find any locations matching that request in the archives."

    filename = f"{layer}_{specific_item.replace(' ', '_') if specific_item else category}_map.png"
    return map_manager.generate_map_image(locations, layer, filename)


def run_compendium_search(query: str) -> str:
    entry = compendium_manager.find_entry(query)
    formatted = format_entry_for_agent(entry)
    desc = formatted["description"]
    img = formatted["image_url"]
    return f"{desc}\n|||IMAGE_URL:{img}|||" if img else desc

tools = [
    Tool(name="SearchIgnWiki", func=get_ign_data_for_agent, description="Use this tool FIRST to find accurate descriptions and images for any specific creature, monster, or item. Also use this as a backup if a map cannot be generated."),
    Tool(name="SearchTotkCompendium", func=run_compendium_search, description="A backup tool. Use this ONLY if the SearchIgnWiki tool fails."),
    Tool(name="SearchLoreTranscripts", func=get_relevant_context_from_transcripts, description="Use this for questions about history, story, and characters."),
    Tool(name="SearchYouTubeForWalkthrough", func=search_youtube_for_walkthrough, description="Use this ONLY when a user insists on getting a walkthrough."),
    Tool(name="GenerateMap", func=generate_map_wrapper, description="Use this to generate a map showing locations of items. Requires a `category` and an optional `specific_item` name."),
]

memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

def get_zelda_response(user_input: str, lang: str = 'en') -> str:
    base_prompt = PROMPTS.get(lang, PROMPTS.get('en'))
    language_instruction = f"IMPORTANT: You must respond in {lang}."
    final_system_prompt = SYSTEM_PROMPT_TEMPLATE.format(base_prompt=base_prompt, language_instruction=language_instruction)

    prompt = ChatPromptTemplate.from_messages([
        ("system", final_system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_openai_tools_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, memory=memory, verbose=True, handle_parsing_errors=True)

    logging.info(f"Invoking agent for language: {lang}")
    try:
        response = agent_executor.invoke({"input": user_input})
        return response.get("output", "I... I'm not sure how to respond to that.")
    except Exception as e:
        logging.error(f"An error occurred while getting the agent's response: {e}")
        return "My apologies, I seem to be having trouble focusing. Could you please repeat that?"
