from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from typing import List
import os
import logging
import yaml
from dotenv import load_dotenv
from src.snl_poc.tools.groundx_tool_optimized import OptimizedGroundXTool
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize optimized GroundX tool
max_chunks = int(os.getenv("GROUNDX_MAX_CHUNKS", "3"))  # Reduced for speed
groundx_tool = OptimizedGroundXTool(bucket_name="phoenix", max_chunks=max_chunks)

@CrewBase
class OptimizedPhoenixCrew():
    """Optimized Phoenix Technologies crew for fast knowledge retrieval."""

    agents_config = "config/agents_phoenix_optimized.yaml"
    tasks_config = "config/tasks_phoenix_optimized.yaml"

    def __init__(self):
        self.llm = LLM(
            model="openai/inference-llama4-maverick",
            temperature=0.1,  # Low temperature for consistent, fast responses
            max_tokens=150    # Limit output for concise responses
        )

    @agent
    def rag_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['rag_agent'],
            tools=[groundx_tool],
            llm=self.llm,
            verbose=False,  # Disable verbose for speed
            allow_delegation=False
        )

    @task
    def chat_task(self) -> Task:
        return Task(
            config=self.tasks_config['chat_task'],
            agent=self.rag_agent(),
            output_pydantic=None,
            create_directory=False
        )

    @crew
    def crew(self) -> Crew:
        """Creates the optimized Phoenix Technologies crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,  # Disable verbose for speed
            memory=False,   # Disable memory for speed
            cache=True,     # Enable CrewAI caching
            max_rpm=100,    # Increase rate limit
            max_execution_time=30  # 30 second timeout
        )

    def chat(self, user_message: str) -> str:
        """Optimized chat method with minimal overhead."""
        start_time = time.time()
        
        try:
            print(f"[OPTIMIZED] Processing query: '{user_message[:50]}...'")
            
            # Get context from GroundX
            context_start = time.time()
            groundx_context = groundx_tool._run(user_message)
            context_time = time.time() - context_start
            print(f"[PROFILE] Context retrieval: {context_time:.2f}s")
            
            # Execute task directly without classification overhead
            llm_start = time.time()
            result = self.crew().kickoff(
                inputs={
                    'user_message': user_message,
                    'groundx_context': groundx_context
                }
            )
            llm_time = time.time() - llm_start
            print(f"[PROFILE] LLM execution: {llm_time:.2f}s")
            
            total_time = time.time() - start_time
            print(f"[PROFILE] Total response time: {total_time:.2f}s")
            
            return str(result)
            
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            print(f"[ERROR] {error_msg}")
            return error_msg
