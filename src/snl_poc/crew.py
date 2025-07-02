from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

import os
import logging
from dotenv import load_dotenv
from tools.groundx_tool import GroundXTool
import json
import re
import time


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
        # Create LLM for all agents
        self.agent_llm = LLM(
            model=os.getenv("OPENAI_MODEL_NAME"),
            base_url=os.getenv("OPENAI_API_BASE"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        # Simple cache to prevent duplicate GroundX calls
        self._groundx_cache = {}
        # # logger.info(f"Initialized LLM with model: {os.getenv('OPENAI_MODEL_NAME')}")

  
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
    def chat_task(self) -> Task:
        """Chat task for processing user queries"""
        return Task(
            config=self.tasks_config['chat_task'], # type: ignore[index]
            agent=self.rag_agent(),
            output_file="conversation_output.md"
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
        """Process a chat query using the crew with hierarchical delegation
        
        Args:
            query: User's query/message
            save_to_file: Optional filename to save the output
            history: Optional conversation history string
            output_log_file: Optional filename for the complete conversation log
        """
        try:
            print(f"[DEBUG CREW] chat() called with query: '{query[:50]}...'")
            
            # Validate query is not empty before processing
            if not query or not query.strip():
                print(f"[DEBUG CREW] Empty query detected, returning error message")
                return "Error: Please provide a valid question or query. Empty queries cannot be processed."
            
            # Check cache first to prevent duplicate calls
            cache_key = query.strip().lower()
            if cache_key in self._groundx_cache:
                print(f"[DEBUG CREW] Using cached GroundX result for query")
                groundx_results = self._groundx_cache[cache_key]
            else:
                # FORCE GroundX tool usage by calling it first
                print(f"[DEBUG CREW] Calling GroundX tool directly before CrewAI...")
                groundx_results = groundx_tool._run(query)
                # Only cache successful results (not error messages)
                if not groundx_results.startswith("Error:"):
                    self._groundx_cache[cache_key] = groundx_results
                    print(f"[DEBUG CREW] GroundX returned {len(groundx_results)} chars, cached for future use")
                else:
                    print(f"[DEBUG CREW] GroundX returned error, not caching")
            
            # Include GroundX results in the input to ensure the agent uses them
            inputs = {
                "user_message": query,
                "history": history if history else "",
                "groundx_context": groundx_results  # Add GroundX results as context
            }
            
            print(f"[DEBUG CREW] Starting CrewAI with inputs: user_message={len(query)} chars, history={len(history) if history else 0} chars, groundx_context={len(groundx_results)} chars")
            print(f"[DEBUG CREW] GroundX context preview (last 200 chars): {groundx_results[-200:]}")
            
            crew_instance = self.crew()
            if save_to_file:
                crew_instance.tasks[0].output_file = save_to_file
            if output_log_file:
                crew_instance.output_log_file = output_log_file
            
            llm_start = time.time()
            result = crew_instance.kickoff(inputs=inputs)
            llm_time = time.time() - llm_start
            print(f"[PROFILE] LLM/Agent call took {llm_time:.2f} seconds")
            
            # Get the raw result as string and return it directly (no post-processing)
            formatted_result = str(result)
            print(f"[DEBUG CREW] Raw LLM result type: {type(result)}")
            print(f"[DEBUG CREW] Raw LLM result length: {len(formatted_result)} chars")
            print(f"[DEBUG CREW] Raw LLM result: {formatted_result}")
            print(f"[DEBUG CREW] Looking for PRIMARY_SOURCE in result: {'[PRIMARY_SOURCE:' in formatted_result}")
            return formatted_result
            
        except Exception as e:
            print(f"[DEBUG CREW] Exception in chat: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
