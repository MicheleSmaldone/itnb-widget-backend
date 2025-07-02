#!/usr/bin/env python
import os
import sys
import warnings
from dotenv import load_dotenv
# from mem0 import MemoryClient  # Commented out to disable Mem0
import datetime
import logging
from crew import SnlPoc
import time

# Silence all loggers by default
logging.getLogger().setLevel(logging.WARNING)

# Silence specific noisy libraries
for noisy_logger in [
    "httpx", "LiteLLM", "tools.groundx_tool", "uvicorn", "uvicorn.error", "uvicorn.access"  # Removed "mem0" since it's disabled
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

# Initialize Mem0 client (correct format)
# client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))  # Commented out to disable Mem0

def run():
    """Run the CustomerZero chat loop for continuous interaction"""
    history = []
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.getcwd(), "output")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Create a session-specific log file name with timestamp
    session_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    session_log_file = os.path.join(output_dir, f"full_session_{session_timestamp}.txt")
    
    print("\n=== Swiss National Library Assistant ===")
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
            print("Assistant: Goodbye! It was nice talking to you.")
            break
        
        # Check for save command
        save_to_file = None
        if user_input.lower() == "save":
            # Generate a filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            save_to_file = os.path.join(output_dir, f"conversation_{timestamp}.md")
            
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
        auto_save_file = os.path.join(output_dir, f"response_{timestamp}.md")
        
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
        
        # Store conversation in mem0 - must be a list of messages
        # messages = [
        #     {"role": "user", "content": user_input},
        #     {"role": "assistant", "content": response}
        # ]
        # client.add(messages, user_id="User", output_format="v1.1")  # Commented out to disable Mem0
        
        print(f"Assistant: {response}")
        print(f"\nResponse automatically saved to: {auto_save_file}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        "topic": "AI LLMs",
        'current_year': str(datetime.now().year)
    }
    try:
        SnlPoc().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        SnlPoc().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        "topic": "AI LLMs",
        "current_year": str(datetime.now().year)
    }
    
    try:
        SnlPoc().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")

if __name__ == "__main__":
    run()