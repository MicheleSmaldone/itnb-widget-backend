#!/usr/bin/env python3
"""
Script to run LLM-as-Judge evaluation on your RAG system responses
"""

import sys
import os
import json
from pathlib import Path

# Add the parent directory to the path so we can import from the main codebase
sys.path.append(str(Path(__file__).parent.parent))

from evaluator import LLMJudgeEvaluator
from crew import SnlPoc

def evaluate_rag_system():
    """Run evaluation on the actual RAG system responses"""
    
    # Initialize evaluator and RAG system
    evaluator = LLMJudgeEvaluator()
    rag_system = SnlPoc()
    
    # Load test queries
    queries_file = os.path.join(os.path.dirname(__file__), "queries.json")
    with open(queries_file, 'r') as f:
        data = json.load(f)
    
    results = []
    
    print(f"Running evaluation on {len(data['test_queries'])} queries...")
    
    for i, query_data in enumerate(data["test_queries"], 1):
        query = query_data["query"]
        print(f"\n[{i}/{len(data['test_queries'])}] Evaluating: {query[:60]}...")
        
        try:
            # Get actual response from your RAG system
            response = rag_system.chat(query)
            
            # Evaluate the response
            result = evaluator.evaluate_response(query, response)
            result.query_id = query_data["id"]
            
            results.append(result)
            
            print(f"  ✓ Overall Score: {result.overall_score}/100")
            print(f"    - Query Answered: {result.answered_query['overall_answered']}/5")
            print(f"    - Source Format: {result.source_format['score']}/5")
            print(f"    - Chatbot Quality: {result.chatbot_quality['overall_quality']}/5")
            
        except Exception as e:
            print(f"  ✗ Error evaluating query: {str(e)}")
            continue
    
    # Save results
    output_file = evaluator.save_results(results)
    print(f"\n🎉 Evaluation complete! Results saved to: {output_file}")
    
    # Print summary
    if results:
        avg_score = sum(r.overall_score for r in results) / len(results)
        print(f"\n📊 Summary:")
        print(f"   Average Overall Score: {avg_score:.1f}/100")
        print(f"   Total Queries Evaluated: {len(results)}")

def evaluate_single_query(query: str):
    """Evaluate a single query"""
    
    evaluator = LLMJudgeEvaluator()
    rag_system = SnlPoc()
    
    print(f"Query: {query}")
    print("Getting response from RAG system...")
    
    try:
        response = rag_system.chat(query)
        print(f"Response: {response}")
        
        print("\nEvaluating response...")
        result = evaluator.evaluate_response(query, response)
        
        print(f"\n📊 Evaluation Results:")
        print(f"Overall Score: {result.overall_score}/100")
        print(f"\nDetailed Scores:")
        print(f"  Query Answered: {result.answered_query['overall_answered']}/5")
        print(f"    - {result.answered_query['explanation']}")
        print(f"  Source Format: {result.source_format['score']}/5")
        print(f"    - {result.source_format['explanation']}")
        print(f"  Chatbot Quality: {result.chatbot_quality['overall_quality']}/5")
        print(f"    - {result.chatbot_quality['explanation']}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single query mode
        query = " ".join(sys.argv[1:])
        evaluate_single_query(query)
    else:
        # Batch evaluation mode
        evaluate_rag_system() 