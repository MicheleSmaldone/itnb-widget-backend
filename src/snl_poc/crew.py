from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

import os
import logging
import yaml
from dotenv import load_dotenv
from src.snl_poc.tools.groundx_tool import GroundXTool
import json
import re
import time

# Remove Google Translate dependency - using LLM for translation instead

# Configure logging
# logger = logging.get# logger(__name__)

# Load environment variables
load_dotenv()

# Initialize GroundX tool with configurable max chunks
max_chunks = int(os.getenv("GROUNDX_MAX_CHUNKS", "5"))  # Get from env var or default to 5
groundx_tool = GroundXTool(max_chunks=max_chunks)  # Use configurable number
# logger.info("Initialized GroundXTool")

# Configure memory settings for agents
# memory_config = {
#     "provider": "mem0",
#     "config": {"user_id": "User"},
# }

@CrewBase
class SnlPoc():
    """SnlPoc crew for knowledge retrieval from company documents"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    
    agents: List[BaseAgent]
    tasks: List[Task]

    def __init__(self):
        """Initialize with OpenAI model"""
        # Get model name with fallback
        model_name = os.getenv("OPENAI_MODEL_NAME")
        if not model_name:
            raise ValueError("OPENAI_MODEL_NAME environment variable is required")
            
        # Create LLM for all agents
        self.agent_llm = LLM(
            model=model_name,
            base_url=os.getenv("OPENAI_API_BASE"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        
        model_name_translation = os.getenv("OPENAI_MODEL_NAME-2")

        # Create separate LLM instance specifically for translation using granite
        self.translation_llm = LLM(
            model=model_name_translation,
            base_url=os.getenv("OPENAI_API_BASE-2"),
            api_key=os.getenv("OPENAI_API_KEY-2"),
        )
        
        # Simple cache to prevent duplicate GroundX calls
        self._groundx_cache = {}
        # Translation cache to avoid repeated translations
        self._translation_cache = {}
        
        # Load task configurations for config-driven prompts
        self._task_configs = self._load_task_configs()
        
        print(f"[DEBUG CREW] Initialized LLMs - Agent: {model_name}, Translation: {model_name_translation}")

    def _load_task_configs(self) -> dict:
        """Load task configurations from tasks.yaml"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), "config", "tasks.yaml")
            with open(config_path, 'r', encoding='utf-8') as f:
                configs = yaml.safe_load(f)
            print(f"[DEBUG CREW] Loaded {len(configs)} task configurations")
            return configs
        except Exception as e:
            print(f"[ERROR] Failed to load task configs: {e}")
            return {}

    def _get_system_prompt_from_config(self, query_type: str) -> str:
        """Get system prompt from task configuration"""
        task_key = f"{query_type}_chat_task"
        
        # Special handling for website queries (uses website_chat_task)
        if query_type == 'website':
            task_key = "website_chat_task"
        
        if task_key not in self._task_configs:
            print(f"[WARN] No config found for {task_key}, using fallback")
            return "You are a helpful assistant. Answer based on the provided context."
        
        task_config = self._task_configs[task_key]
        description = task_config.get('description', '')
        
        # Convert YAML description to system prompt
        system_prompt = f"""You are a specialized assistant.

{description}

Remember to always:
- Use ONLY the information provided in the GroundX context
- Answer in the same language as the user's question
- Be precise and follow the formatting guidelines exactly"""
        
        return system_prompt

    def _translate_and_classify(self, text: str) -> tuple[str, str]:
        """
        Translate text to English and classify query type.
        Returns: (translated_text, query_type)
        query_type: 'website', 'thesis', 'books', 'posters'
        """
        if not text or not text.strip():
            return text, 'website'
        
        # Check cache first (enhanced to include classification)
        cache_key = text.strip().lower()
        if cache_key in self._translation_cache:
            print(f"[DEBUG CREW] Using cached translation and classification")
            return self._translation_cache[cache_key]
        
        try:
            # Enhanced prompt for translation AND 4-way classification
            classification_prompt = f"""You have two tasks:

1. TRANSLATE: Translate the following text to English. If already in English, return unchanged.
2. CLASSIFY: Determine the query type based on content and intent.

CLASSIFICATION RULES:
- 'thesis': Academic questions about research papers, dissertations, thesis documents, academic analysis (keywords: thesis/dissertation/research/study/analysis/academic/chapter)
- 'books': Questions about finding books, literature, novels, authors, book collections (keywords: book/author/literature/novel/publication/find books)
- 'posters': Questions about exhibition posters, art exhibitions, gallery displays, museum shows (keywords: poster/exhibition/expo/gallery/museum/display/show)
- 'website': General library information, services, procedures, opening hours, access policies (keywords: library/service/access/procedure/policy/hours/register)

Text: {text}

Respond in this exact format:
TRANSLATION: [translated text]
TYPE: [website/thesis/books/posters]"""
            
            print(f"[DEBUG CREW] Sending translation+classification request for: '{text[:50]}...'")
            
            response = self.translation_llm.call([{"role": "user", "content": classification_prompt}])
            
            # Extract response content
            if hasattr(response, 'content'):
                response_text = response.content.strip()
            else:
                response_text = str(response).strip()
            
            # Parse the structured response
            lines = response_text.split('\n')
            translated_text = text  # fallback
            query_type = 'website'  # fallback
            
            for line in lines:
                if line.startswith('TRANSLATION:'):
                    translated_text = line.replace('TRANSLATION:', '').strip()
                elif line.startswith('TYPE:'):
                    type_value = line.replace('TYPE:', '').strip().lower()
                    if type_value in ['website', 'thesis', 'books', 'posters']:
                        query_type = type_value
            
            print(f"[DEBUG CREW] Classification result: '{translated_text[:50]}...' -> {query_type}")
            
            # Cache the result
            result = (translated_text, query_type)
            self._translation_cache[cache_key] = result
            return result
                
        except Exception as e:
            print(f"[DEBUG CREW] Translation+classification failed: {e}, using defaults")
            result = (text, 'website')
            self._translation_cache[cache_key] = result
            return result

    @agent
    def rag_agent(self) -> Agent:
        """RAG knowledge retrieval agent"""
        return Agent(
            config=self.agents_config['rag_agent'], # type: ignore[index]
            #memory=True,
            verbose=True,
            allow_delegation=False,
            llm=self.agent_llm,
            tools=[]  # Remove tool since we call it manually before CrewAI
        )

    @task
    def website_chat_task(self) -> Task:
        """Chat task for website-related queries (current functionality)"""
        return Task(
            config=self.tasks_config['website_chat_task'],
            agent=self.rag_agent(),
            output_file="conversation_output.md"
        )

    @task  
    def thesis_chat_task(self) -> Task:
        """Chat task for thesis discussion"""
        return Task(
            config=self.tasks_config['thesis_chat_task'],
            agent=self.thesis_agent(),
            output_file="conversation_output.md"
        )

    @task
    def books_chat_task(self) -> Task:
        """Chat task for book search and information"""
        return Task(
            config=self.tasks_config['books_chat_task'],
            agent=self.books_agent(),
            output_file="conversation_output.md"
        )

    @task
    def posters_chat_task(self) -> Task:
        """Chat task for poster and exhibition information"""
        return Task(
            config=self.tasks_config['posters_chat_task'],
            agent=self.posters_agent(),
            output_file="conversation_output.md"
        )

    @agent
    def thesis_agent(self) -> Agent:
        """Agent specialized for thesis discussion"""
        return Agent(
            config=self.agents_config['thesis_agent'],
            verbose=True,
            allow_delegation=False,
            llm=self.agent_llm,
            tools=[]
        )

    @agent
    def books_agent(self) -> Agent:
        """Agent specialized for book search and information"""
        return Agent(
            config=self.agents_config['books_agent'],
            verbose=True,
            allow_delegation=False,
            llm=self.agent_llm,
            tools=[]
        )

    @agent
    def posters_agent(self) -> Agent:
        """Agent specialized for poster and exhibition information"""
        return Agent(
            config=self.agents_config['posters_agent'],
            verbose=True,
            allow_delegation=False,
            llm=self.agent_llm,
            tools=[]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the SnlPoc crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            #memory=True,
            #memory_config=memory_config,
            output_log_file="output/full_conversation_log.txt",
            # CrewAI automatically saves outputs to these locations:
            # - Task outputs: conversation_output.md (from task config)  
            # - Crew logs: output/full_conversation_log.txt
            # - Final results: Can be saved via save_to_file parameter
            share_crew=False  # Set to True if you want to share crew runs publicly
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
    
    def chat(self, query: str, save_to_file: str = None, history: str = None, output_log_file: str = None) -> str:
        """Process a chat query using a single unified call"""
        try:
            print(f"[DEBUG CREW] chat() called with query: '{query[:50] if query else 'None'}...'")
            
            if not query or not query.strip():
                return "Error: Please provide a valid question or query."
            
            # Translate and classify the query
            translated_query, query_type = self._translate_and_classify(query)
            print(f"[DEBUG CREW] Query classified as: {query_type}")
            
            # Get GroundX results (cached)
            cache_key = translated_query.strip().lower()
            if cache_key in self._groundx_cache:
                groundx_results = self._groundx_cache[cache_key]
            else:
                groundx_results = groundx_tool._run(translated_query)
                if not groundx_results.startswith("Error:"):
                    self._groundx_cache[cache_key] = groundx_results
            
            if groundx_results.startswith("Error:"):
                groundx_results = "There is no available information for me to assist you."
            
            # Create unified prompt based on query type
            system_prompt = self._get_system_prompt_from_config(query_type)
            
            # Create the unified prompt
            user_prompt = f"""Question: {query}

                            History: {history if history else "None"}

                            GroundX Context:
                            {groundx_results}

                            Answer:"""
            
            # Direct LLM call (skip CrewAI overhead)
            print(f"[DEBUG CREW] Making direct LLM call for {query_type} mode")
            llm_start = time.time()
            
            response = self.agent_llm.call([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])
            
            llm_time = time.time() - llm_start
            print(f"[PROFILE] Direct LLM call took {llm_time:.2f} seconds")
            
            # Extract response
            if hasattr(response, 'content'):
                result = response.content.strip()
            else:
                result = str(response).strip()
            
            return result
            
        except Exception as e:
            print(f"[DEBUG CREW] Exception in chat: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
