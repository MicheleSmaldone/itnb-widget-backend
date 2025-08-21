#!/usr/bin/env python
import os
import sys
import warnings
from dotenv import load_dotenv
import time
import logging
from crew_phoenix_optimized import OptimizedPhoenixCrew

# Silence all loggers for speed
logging.getLogger().setLevel(logging.WARNING)
for noisy_logger in ["httpx", "LiteLLM", "uvicorn", "crewai"]:
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

# Suppress warnings
warnings.filterwarnings("ignore")

# Load environment variables
load_dotenv()

def run_performance_test():
    """Run performance tests with optimized configuration."""
    print("🚀 Testing Optimized Phoenix Technologies Chatbot")
    print("=" * 60)
    
    crew = OptimizedPhoenixCrew()
    
    # Test queries with expected fast responses
    test_queries = [
        "What is Phoenix Technologies?",
        "Tell me about Sovereign Cloud",
        "What AI services do you offer?",
        "What cybersecurity solutions does Phoenix provide?",
        "How does Phoenix Technologies help with data sovereignty?",
        "What is Phoenix Technologies?",  # Duplicate for cache testing
    ]
    
    total_start = time.time()
    results = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n[TEST {i}/6] Query: {query}")
        print("-" * 50)
        
        start = time.time()
        response = crew.chat(query)
        duration = time.time() - start
        
        results.append(duration)
        
        print(f"⏱️  Response time: {duration:.2f}s")
        print(f"📝 Response: {response[:200]}...")
        
        # Color coding for performance
        if duration <= 3:
            print("✅ EXCELLENT (≤3s)")
        elif duration <= 7:
            print("🟡 GOOD (≤7s)") 
        else:
            print("🔴 NEEDS IMPROVEMENT (>7s)")
    
    total_time = time.time() - total_start
    avg_time = sum(results) / len(results)
    
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"Total test time: {total_time:.2f}s")
    print(f"Average response time: {avg_time:.2f}s")
    print(f"Fastest response: {min(results):.2f}s")
    print(f"Slowest response: {max(results):.2f}s")
    
    fast_responses = sum(1 for t in results if t <= 7)
    print(f"Responses ≤7s: {fast_responses}/{len(results)} ({fast_responses/len(results)*100:.1f}%)")
    
    excellent_responses = sum(1 for t in results if t <= 3)
    print(f"Excellent responses ≤3s: {excellent_responses}/{len(results)} ({excellent_responses/len(results)*100:.1f}%)")

def run_interactive():
    """Run interactive chat session."""
    print("🚀 Phoenix Technologies Assistant (Optimized)")
    print("Type 'exit' to quit, 'clear_cache' to clear cache")
    print("=" * 50)
    
    crew = OptimizedPhoenixCrew()
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'bye']:
                break
            elif user_input.lower() == 'clear_cache':
                crew.rag_agent().tools[0].clear_cache()
                print("Cache cleared!")
                continue
            elif not user_input:
                continue
            
            start = time.time()
            response = crew.chat(user_input)
            duration = time.time() - start
            
            print(f"\nAssistant: {response}")
            print(f"\n⏱️ Response time: {duration:.2f}s")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    print("\nGoodbye! 👋")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_performance_test()
    else:
        run_interactive()
