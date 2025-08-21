#!/usr/bin/env python
import os
import sys
import warnings
from dotenv import load_dotenv
import datetime
import logging
from crew_phoenix import SnlPoc  # Import Phoenix version
import time

# Silence all loggers by default
logging.getLogger().setLevel(logging.WARNING)

# Silence specific noisy libraries
for noisy_logger in [
    "httpx", "LiteLLM", "tools.groundx_tool", "uvicorn", "uvicorn.error", "uvicorn.access"
]:
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress warnings
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# Load environment variables
load_dotenv()

def run():
    """Run the Phoenix Technologies chat loop for continuous interaction"""
    history = []
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.getcwd(), "output")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Create a session-specific log file name with timestamp
    session_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    session_log_file = os.path.join(output_dir, f"phoenix_session_{session_timestamp}.txt")
    
    print("\n=== Phoenix Technologies Assistant ===")
    print("Ask me about Phoenix Technologies' AI solutions, cloud infrastructure,")
    print("cybersecurity services, and Swiss sovereign computing!")
    print("Type 'exit', 'quit', or 'bye' to end the conversation.")
    print("Type 'save' to save the current response to a file.")
    print(f"Full session log will be saved to: {session_log_file}")
    print()
    
    # Initialize crew instance
    crew_instance = SnlPoc()
    
    # Configure the crew to use the session-specific log file
    crew_instance.crew().output_log_file = session_log_file
    
    while True:
        user_input = input("User: ")
        
        # Check for exit command
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Assistant: Goodbye! Thank you for learning about Phoenix Technologies.")
            break
        
        # Check for save command
        save_to_file = None
        if user_input.lower() == "save":
            # Generate a filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            save_to_file = os.path.join(output_dir, f"phoenix_conversation_{timestamp}.md")
            
            # Get the last response to save
            if history:
                last_response = history[-1].replace("Assistant: ", "")
                with open(save_to_file, "w") as f:
                    f.write(last_response)
                print(f"Assistant: Last response saved to {save_to_file}")
            else:
                print("Assistant: No response to save yet.")
            continue
        
        chat_history = "\n".join(history)
        
        inputs = {
            "user_message": f"{user_input}",
            "history": f"{chat_history}",
        }
        
        # Create dynamic filename for automatic saving
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        auto_save_file = os.path.join(output_dir, f"phoenix_response_{timestamp}.md")
        
        # Use the crew's chat method which supports file saving
        start = time.time()
        response = crew_instance.chat(
            user_input, 
            save_to_file=auto_save_file,
            history=chat_history,
            output_log_file=session_log_file
        )
        print("LLM call took", time.time() - start)
        
        history.append(f"User: {user_input}")
        history.append(f"Assistant: {response}")
        
        print(f"Assistant: {response}")
        print(f"\nResponse automatically saved to: {auto_save_file}")

def test_phoenix():
    """Test the Phoenix Technologies assistant with sample queries"""
    print("\n=== Testing Phoenix Technologies Assistant ===")
    
    # Initialize crew instance
    crew_instance = SnlPoc()
    
    # Test queries
    test_queries = [
        "What is Phoenix Technologies?",
        "Tell me about Sovereign Cloud",
        "What AI services do you offer?",
        "What cybersecurity solutions does Phoenix provide?",
        "Qu'est-ce que Phoenix Technologies?",  # French test
        "Was ist die Sovereign Cloud?",  # German test
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Test {i}: {query} ---")
        start = time.time()
        response = crew_instance.chat(query)
        duration = time.time() - start
        print(f"Response ({duration:.2f}s): {response}")
        print("-" * 80)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_phoenix()
    else:
        run()
