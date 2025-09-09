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

# Configure logging
# logger = logging.get# logger(__name__)

# Load environment variables
load_dotenv()

# Initialize GroundX tool with configurable max chunks for ITNB bucket
max_chunks = int(os.getenv("GROUNDX_MAX_CHUNKS", "2"))  # Get from env var or default to 2
groundx_tool = GroundXTool(bucket_id=69, max_chunks=max_chunks)  # Use ITNB bucket ID 69 directly
# logger.info("Initialized GroundXTool")

@CrewBase
class SnlPoc():
    """ITNB crew for knowledge retrieval from company documents"""

    agents_config = "config/agents_itnb.yaml"
    tasks_config = "config/tasks_itnb.yaml"
    
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
        
        model_name_translation = os.getenv("OPENAI_MODEL_NAME_2") or os.getenv("OPENAI_MODEL_NAME")

        # Create separate LLM instance specifically for translation using granite
        self.translation_llm = LLM(
            model=model_name_translation,
            base_url=os.getenv("OPENAI_API_BASE_2") or os.getenv("OPENAI_API_BASE"),
            api_key=os.getenv("OPENAI_API_KEY_2") or os.getenv("OPENAI_API_KEY"),
        )
        
        # Simple cache to prevent duplicate GroundX calls
        self._groundx_cache = {}
        # Translation cache to avoid repeated translations
        self._translation_cache = {}
        
        # Load task configurations for config-driven prompts
        self._task_configs = self._load_task_configs()
        
        print(f"[DEBUG CREW] Initialized Phoenix Technologies LLMs - Agent: {model_name}, Translation: {model_name_translation}")

    def _load_task_configs(self) -> dict:
        """Load task configurations from tasks_itnb.yaml"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), "config", "tasks_itnb.yaml")
            with open(config_path, 'r', encoding='utf-8') as f:
                configs = yaml.safe_load(f)
            print(f"[DEBUG CREW] Loaded {len(configs)} Phoenix Technologies task configurations")
            return configs
        except Exception as e:
            print(f"[ERROR] Failed to load Phoenix task configs: {e}")
            return {}

    def _get_system_prompt_from_config(self, query_type: str, current_query_language: str = None) -> str:
        """Get system prompt from task configuration with explicit language override"""
        # For Phoenix Technologies, we only have website queries
        task_key = "website_chat_task"
        
        if task_key not in self._task_configs:
            print(f"[WARN] No config found for {task_key}, using fallback")
            return "You are a helpful Phoenix Technologies assistant. Answer based on the provided context."
        
        task_config = self._task_configs[task_key]
        description = task_config.get('description', '')
        
        # Add explicit language override if provided
        language_override = ""
        if current_query_language:
            language_override = f"""
CRITICAL LANGUAGE RULE: 
- The user's CURRENT question is in {current_query_language}
- You MUST respond ONLY in {current_query_language}
- IGNORE any other languages in the conversation history
- Base your language ONLY on the current user question, not the history
"""
        
        # Convert YAML description to system prompt
        system_prompt = f"""{language_override}

You are a specialized Phoenix Technologies assistant.

{description}

Remember to always:
- Use ONLY the information provided in the GroundX context about Phoenix Technologies
- Answer in the same language as the user's CURRENT question (ignore history language)
- Be precise and follow the formatting guidelines exactly
- Focus on Phoenix Technologies' AI solutions, cloud infrastructure, cybersecurity, and Swiss sovereign computing"""
        
        return system_prompt

    def _translate_and_classify(self, text: str) -> tuple[str, str]:
        """
        Translate text to English and classify query type.
        For Phoenix Technologies, we only have 'website' queries.
        Returns: (translated_text, query_type)
        """
        if not text or not text.strip():
            return text, 'website'
        
        # Check cache first
        cache_key = text.strip().lower()
        if cache_key in self._translation_cache:
            print(f"[DEBUG CREW] Using cached translation for Phoenix query")
            return self._translation_cache[cache_key]
        
        try:
            # Enhanced prompt for translation (no classification needed for Phoenix)
            translation_prompt = f"""You have one task:

TRANSLATE: Translate the following text to English. If already in English, return unchanged.

Text: {text}

Respond with only the translated text:"""
            
            print(f"[DEBUG CREW] Sending translation request for Phoenix query: '{text[:50]}...'")
            
            response = self.translation_llm.call([{"role": "user", "content": translation_prompt}])
            
            # Extract response content
            if hasattr(response, 'content'):
                translated_text = response.content.strip()
            else:
                translated_text = str(response).strip()
            
            print(f"[DEBUG CREW] Translation result: '{translated_text[:50]}...' -> website")
            
            # For Phoenix Technologies, everything is a website query
            result = (translated_text, 'website')
            self._translation_cache[cache_key] = result
            return result
                
        except Exception as e:
            print(f"[DEBUG CREW] Translation failed: {e}, using defaults")
            result = (text, 'website')
            self._translation_cache[cache_key] = result
            return result

    def _detect_query_language(self, query: str) -> str:
        """Detect the language of the current query only"""
        try:
            # Simple language detection prompt
            detection_prompt = f"""Detect the language of this text and respond with only the language name in English:

Text: "{query}"

Language:"""
            
            response = self.translation_llm.call([{"role": "user", "content": detection_prompt}])
            
            if hasattr(response, 'content'):
                language = response.content.strip().lower()
            else:
                language = str(response).strip().lower()
            
            # Normalize common language names
            if 'english' in language or 'en' == language:
                return 'English'
            elif 'french' in language or 'français' in language or 'fr' == language:
                return 'French'
            elif 'german' in language or 'deutsch' in language or 'de' == language:
                return 'German'
            elif 'italian' in language or 'italiano' in language or 'it' == language:
                return 'Italian'
            else:
                return language.title()
                
        except Exception as e:
            print(f"[DEBUG CREW] Language detection failed: {e}")
            return 'English'  # fallback

    @agent
    def rag_agent(self) -> Agent:
        """RAG knowledge retrieval agent for Phoenix Technologies"""
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
        """Chat task for Phoenix Technologies website queries"""
        return Task(
            config=self.tasks_config['website_chat_task'],
            agent=self.rag_agent(),
            output_file="conversation_output.md"
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Phoenix Technologies crew"""
        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            #memory=True,
            output_log_file="output/full_conversation_log.txt",
            share_crew=False  # Set to True if you want to share crew runs publicly
        )
    
    def chat(self, query: str, save_to_file: str = None, history: str = None, output_log_file: str = None) -> str:
        """Process a chat query for Phoenix Technologies"""
        try:
            print(f"[DEBUG CREW] Phoenix Technologies chat() called with query: '{query[:50] if query else 'None'}...'")
            
            if not query or not query.strip():
                return "Error: Please provide a valid question or query."
            
            # Translate the query (classification always returns 'website' for Phoenix)
            translated_query, query_type = self._translate_and_classify(query)
            print(f"[DEBUG CREW] Phoenix query classified as: {query_type}")
            
            # Detect the current query language
            current_query_language = self._detect_query_language(query)
            print(f"[DEBUG CREW] Current query language detected: {current_query_language}")
            
            # Get GroundX results (cached)
            cache_key = translated_query.strip().lower()
            if cache_key in self._groundx_cache:
                groundx_results = self._groundx_cache[cache_key]
            else:
                groundx_results = groundx_tool._run(translated_query)
                if not groundx_results.startswith("Error:"):
                    self._groundx_cache[cache_key] = groundx_results
            
            if groundx_results.startswith("Error:"):
                groundx_results = "There is no available information about Phoenix Technologies for me to assist you."
            
            # Create unified prompt based on query type (always 'website' for Phoenix)
            system_prompt = self._get_system_prompt_from_config(query_type, current_query_language)
            
            # Create the unified prompt
            user_prompt = f"""Question: {query}

                            History: {history if history else "None"}

                            GroundX Context:
                            {groundx_results}

                            Answer:"""
            
            # Direct LLM call (skip CrewAI overhead)
            print(f"[DEBUG CREW] Making direct LLM call for Phoenix Technologies {query_type} mode")
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
            print(f"[DEBUG CREW] Exception in Phoenix Technologies chat: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
