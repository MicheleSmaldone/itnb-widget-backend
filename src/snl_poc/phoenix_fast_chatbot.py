#!/usr/bin/env python
"""
Ultra-fast Phoenix Technologies chatbot with direct LLM calls and aggressive optimizations.
Target: 3-7 second response times.
"""

import os
import time
import json
import hashlib
import asyncio
from typing import Dict, Optional
from dotenv import load_dotenv
from groundx import GroundX

# Load environment
load_dotenv()

class FastPhoenixChatbot:
    """Ultra-optimized ITNB chatbot."""
    
    def __init__(self):
        # Initialize GroundX with on-prem configuration
        self.groundx = GroundX(
            api_key=os.getenv("GROUNDX_API_KEY", "5c49be10-d228-4dd8-bbb0-d59300698ef6"),
            base_url=os.getenv("GROUNDX_BASE_URL", "https://groundx-service-eyelevel.apps.eyelevel.kvant.cloud/api")
        )
        self.bucket_id = 25  # ITNB bucket
        
        # Initialize OpenAI with your existing configuration
        from crewai import LLM
        self.llm = LLM(model="openai/inference-llama4-maverick", temperature=0.1)
        
        # Cache for responses
        self.cache: Dict[str, str] = {}
        self.cache_timestamps: Dict[str, float] = {}
        self.cache_ttl = 3600  # 1 hour
        
        # Optimized prompt template with few-shot examples (MANDATORY Markdown format)
        self.prompt_template = """You are ITNB's AI assistant. You MUST answer in 30-50 words using provided context, formatted in Markdown.

CRITICAL: YOU MUST FORMAT YOUR RESPONSE IN MARKDOWN - NO PLAIN TEXT ALLOWED.

EXAMPLES:
Q: "What is Sovereign Cloud?"
A: "**ITNB's** *Sovereign Cloud* provides **Swiss data sovereignty** with complete control over infrastructure and data location, ensuring *compliance* with local regulations while offering enterprise-grade cloud services."

Q: "What AI services do you offer?"  
A: "**ITNB** offers:
* **AI Model as a Service**
* AI infrastructure hosting  
* AI workload optimization on **sovereign Swiss infrastructure**
* **GPU-as-a-Service** and custom AI deployment solutions"

Q: "Tell me about cybersecurity"
A: "**Phoenix Technologies** provides:
* **Sovereign Endpoint Security**
* 24/7 **SOC** services
* Comprehensive cybersecurity solutions designed for *Swiss compliance* and data protection requirements

[Source](https://phoenix-technologies.ch/en/cybersecurity)"

MANDATORY RULES:
- Answer in SAME LANGUAGE as question
- Use 30-50 words maximum
- **MANDATORY MARKDOWN FORMATTING**:
  * Write "**Phoenix Technologies**" (not "Phoenix Technologies") EVERY TIME
  * Use **bold** for ALL product/service names
  * Use *italics* for emphasis words like compliance, sovereignty, security
  * Use bullet points (*) for ANY list of 2+ items
- Convert ALL [PRIMARY_SOURCE: URL] markers to markdown link format: [Source](URL)
- If no relevant info: "I don't have information about that topic"

CONTEXT: {context}

QUESTION: {question}

MARKDOWN ANSWER:"""
    
    def _get_cache_key(self, query: str) -> str:
        """Generate cache key."""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check cache validity."""
        if cache_key not in self.cache_timestamps:
            return False
        return (time.time() - self.cache_timestamps[cache_key]) < self.cache_ttl
    
    def _search_groundx(self, query: str) -> str:
        """Fast GroundX search with error handling."""
        try:
            print(f"[SEARCH] GroundX query: '{query[:50]}...'")
            start = time.time()
            
            # Single optimized search call
            result = self.groundx.search.content(
                id=self.bucket_id,
                query=query.strip(),
                verbosity=1,
                n=1  # Limit to 3 chunks for speed
            )
            
            search_time = time.time() - start
            print(f"[PROFILE] GroundX search: {search_time:.2f}s")
            
            # Extract content and sources
            texts = []
            sources = set()
            
            if (hasattr(result, 'search') and 
                hasattr(result.search, 'results') and 
                result.search.results):
                
                for chunk in result.search.results:
                    if hasattr(chunk, 'text') and chunk.text:
                        try:
                            # Try to parse as JSON to extract source_url
                            chunk_data = json.loads(chunk.text)
                            if isinstance(chunk_data, dict):
                                # Extract clean text content
                                content_parts = []
                                for key, value in chunk_data.items():
                                    if key == 'source_url':
                                        sources.add(value)
                                    elif key not in ['technical_specs', 'metadata'] and value:
                                        if isinstance(value, str) and len(value.strip()) > 10:
                                            content_parts.append(f"{key}: {value.strip()}")
                                        elif isinstance(value, list):
                                            content_parts.append(f"{key}: {', '.join(str(v) for v in value if v)}")
                                
                                if content_parts:
                                    texts.append(" | ".join(content_parts))
                                    
                        except json.JSONDecodeError:
                            # Use raw text if not JSON
                            texts.append(chunk.text)
            
            # Build context
            context = "\n\n".join(texts) if texts else "No relevant information found."
            
            # Add source markers
            if sources:
                source_markers = [f"[PRIMARY_SOURCE: {url}]" for url in sources]
                context += "\n\n" + "\n".join(source_markers)
            
            print(f"[SEARCH] Found {len(texts)} chunks, {len(sources)} sources")
            return context
            
        except Exception as e:
            print(f"[ERROR] GroundX search failed: {e}")
            return f"Search error: {str(e)}"
    
    def _call_llm(self, prompt: str) -> str:
        """Fast LLM call with optimizations."""
        try:
            print(f"[LLM] Calling model...")
            start = time.time()
            
            # Use CrewAI LLM interface
            response = self.llm.call([{"role": "user", "content": prompt}])
            
            llm_time = time.time() - start
            print(f"[PROFILE] LLM call: {llm_time:.2f}s")
            
            return response.strip() if response else "No response generated."
            
        except Exception as e:
            print(f"[ERROR] LLM call failed: {e}")
            return f"Response generation error: {str(e)}"
    
    def chat(self, user_message: str) -> str:
        """Main chat method with aggressive optimization."""
        if not user_message or not user_message.strip():
            return "Please provide a question about Phoenix Technologies."
        
        total_start = time.time()
        
        # Check cache first
        cache_key = self._get_cache_key(user_message)
        if cache_key in self.cache and self._is_cache_valid(cache_key):
            cache_time = time.time() - total_start
            print(f"[CACHE HIT] Response time: {cache_time:.2f}s")
            return self.cache[cache_key]
        
        try:
            # Step 1: Search GroundX (single call)
            context = self._search_groundx(user_message)
            
            # Step 2: Generate response
            prompt = self.prompt_template.format(
                context=context,
                question=user_message
            )
            
            response = self._call_llm(prompt)
            
            # Cache the result
            self.cache[cache_key] = response
            self.cache_timestamps[cache_key] = time.time()
            
            total_time = time.time() - total_start
            print(f"[TOTAL] Response time: {total_time:.2f}s")
            
            return response
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(f"[ERROR] {error_msg}")
            return error_msg
    
    def clear_cache(self):
        """Clear response cache."""
        self.cache.clear()
        self.cache_timestamps.clear()
        print("Cache cleared!")


def run_performance_test():
    """Run comprehensive performance tests."""
    print("🚀 Fast Phoenix Technologies Chatbot - Performance Test")
    print("=" * 60)
    
    chatbot = FastPhoenixChatbot()
    
    test_queries = [
        "What is Phoenix Technologies?",
        "Tell me about Sovereign Cloud", 
        "What AI services do you offer?",
        "What cybersecurity solutions does Phoenix provide?",
        "How does Phoenix Technologies help with data sovereignty?",
        "What is Phoenix Technologies?",  # Duplicate for cache test
        "Tell me about GPU services",
        "What industries does Phoenix Technologies serve?",
    ]
    
    results = []
    total_start = time.time()
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n[TEST {i}/{len(test_queries)}] {query}")
        print("-" * 50)
        
        start = time.time()
        response = chatbot.chat(query)
        duration = time.time() - start
        results.append(duration)
        
        print(f"⏱️  Response time: {duration:.2f}s")
        print(f"📝 Response: {response}")
        
        # Performance classification
        if duration <= 3:
            print("✅ EXCELLENT (≤3s)")
        elif duration <= 7:
            print("🟡 GOOD (≤7s)")
        else:
            print("🔴 NEEDS IMPROVEMENT (>7s)")
    
    # Summary
    total_time = time.time() - total_start
    avg_time = sum(results) / len(results)
    
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"Average response time: {avg_time:.2f}s")
    print(f"Fastest response: {min(results):.2f}s")
    print(f"Slowest response: {max(results):.2f}s")
    
    fast_count = sum(1 for t in results if t <= 7)
    excellent_count = sum(1 for t in results if t <= 3)
    
    print(f"Target met (≤7s): {fast_count}/{len(results)} ({fast_count/len(results)*100:.1f}%)")
    print(f"Excellent (≤3s): {excellent_count}/{len(results)} ({excellent_count/len(results)*100:.1f}%)")


def run_interactive():
    """Interactive chat session."""
    print("🚀 Fast Phoenix Technologies Assistant")
    print("Commands: 'exit', 'clear_cache', 'test'")
    print("=" * 50)
    
    chatbot = FastPhoenixChatbot()
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['exit', 'quit']:
                break
            elif user_input.lower() == 'clear_cache':
                chatbot.clear_cache()
                continue
            elif user_input.lower() == 'test':
                run_performance_test()
                continue
            elif not user_input:
                continue
            
            response = chatbot.chat(user_input)
            print(f"\nAssistant: {response}")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    print("Goodbye! 👋")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_performance_test()
    else:
        run_interactive()
