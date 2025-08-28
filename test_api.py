#!/usr/bin/env python3
"""
Quick test script for Phoenix Widget Backend API
"""
import requests
import json
import time

API_BASE = "https://phoenix-widget-backend-production.up.railway.app"

def test_health():
    """Test the health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"✅ Health check passed: {data}")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_chat(message, history=""):
    """Test the chat endpoint"""
    print(f"\n💬 Testing chat with message: '{message}'")
    try:
        start_time = time.time()
        
        payload = {
            "message": message,
            "history": history
        }
        
        response = requests.post(
            f"{API_BASE}/chat",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60  # LLM calls can take time
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Chat response received in {response_time:.2f}s")
        print(f"📝 Response: {data.get('response', 'No response field')}")
        return data.get('response', '')
        
    except requests.exceptions.Timeout:
        print(f"⏰ Request timed out after 60 seconds")
        return None
    except Exception as e:
        print(f"❌ Chat request failed: {e}")
        if hasattr(e, 'response') and e.response:
            try:
                error_data = e.response.json()
                print(f"🔍 Error details: {error_data}")
            except:
                print(f"🔍 Raw error response: {e.response.text}")
        return None

def run_comprehensive_test():
    """Run a comprehensive test suite"""
    print("🚀 Starting Phoenix Widget Backend API Tests")
    print("=" * 60)
    
    # Test 1: Health check
    if not test_health():
        print("❌ Health check failed. Stopping tests.")
        return
    
    # Test 2: Simple chat messages
    test_messages = [
        "What is Phoenix Technologies?",
        "Tell me about Sovereign Cloud",
        "What AI services do you offer?",
        "What cybersecurity solutions does Phoenix provide?",
        "Hello, how can you help me?",
    ]
    
    history = ""
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- Test {i}/{len(test_messages)} ---")
        response = test_chat(message, history)
        
        if response:
            # Update history for next test
            history += f"User: {message}\nAssistant: {response}\n"
        else:
            print("⚠️  Failed to get response, continuing without updating history")
        
        # Small delay between requests
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print("🏁 Test suite completed!")

def interactive_test():
    """Interactive chat session"""
    print("🚀 Interactive Phoenix Widget Backend Test")
    print("Type 'quit' to exit")
    print("-" * 40)
    
    if not test_health():
        print("❌ Backend not healthy. Exiting.")
        return
    
    history = ""
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("👋 Goodbye!")
            break
            
        if not user_input:
            continue
            
        response = test_chat(user_input, history)
        
        if response:
            print(f"🤖 Assistant: {response}")
            history += f"User: {user_input}\nAssistant: {response}\n"
        else:
            print("❌ Failed to get response from assistant")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_test()
    else:
        run_comprehensive_test()

