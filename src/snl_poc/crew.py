from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

import os
import logging
from dotenv import load_dotenv
from tools.groundx_tool import GroundXTool


# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize GroundX tool
groundx_tool = GroundXTool()
logger.info("Initialized GroundXTool")

# Configure memory settings for agents
memory_config = {
    "provider": "mem0",
    "config": {"user_id": "User"},
}

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
        
        logger.info(f"Initialized LLM with model: {os.getenv('OPENAI_MODEL_NAME')}")

  
    @agent
    def rag_agent(self) -> Agent:
        """RAG knowledge retrieval agent"""
        return Agent(
            config=self.agents_config['rag_agent'], # type: ignore[index]
            memory=True,
            verbose=True,
            allow_delegation=False,
            llm=self.agent_llm,
            tools=[groundx_tool]
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
            memory=True,
            memory_config=memory_config,
            output_log_file="output/full_conversation_log.txt"
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
            inputs = {
                "user_message": query,
                "history": history if history else ""
            }
            
            # Create crew instance
            crew_instance = self.crew()
            
            # Set output file if provided
            if save_to_file:
                # Update the output_file for the task
                crew_instance.tasks[0].output_file = save_to_file
                
            # Set output log file if provided
            if output_log_file:
                crew_instance.output_log_file = output_log_file
            
            result = crew_instance.kickoff(inputs=inputs)
            return str(result)
        except Exception as e:
            logger.error(f"Error during chat: {str(e)}")
            return f"Sorry, I encountered an error: {str(e)}"
