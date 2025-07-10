#!/usr/bin/env python3
"""
Test the 4-way classification system for different query types
"""

import sys
import os
import json
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crew import SnlPoc

def test_classification():
    """Test the 4-way classification with different query types"""
    
    print("🧪 Testing 4-way Query Classification System")
    print("=" * 60)
    
    # Initialize the crew
    crew = SnlPoc()
    
    # Test queries for each category
    test_queries = [
        # Website queries
        ("How do I access the digital collections?", "website"),
        ("What are the library opening hours?", "website"),
        ("How to register for library services?", "website"),
        
        # Thesis queries  
        ("Tell me about Bur's thesis", "thesis"),
        ("What is the main argument in chapter 3?", "thesis"),
        ("Analyze the motion model approach", "thesis"),
        
        # Books queries
        ("Find books by Van Gogh", "books"),
        ("Show me literature about Swiss history", "books"),
        ("What novels are available in the collection?", "books"),
        
        # Posters queries
        ("Van Gogh exhibition posters", "posters"),
        ("What exhibitions were held in 1973?", "posters"),
        ("Show me Kunsthaus Zürich posters", "posters"),
    ]
    
    results = []
    correct = 0
    total = len(test_queries)
    
    for query, expected_type in test_queries:
        print(f"\n🔍 Query: '{query}'")
        print(f"   Expected: {expected_type}")
        
        # Test just the classification (not full chat)
        try:
            translated_query, classified_type = crew._translate_and_classify(query)
            print(f"   Classified: {classified_type}")
            print(f"   Translated: '{translated_query}'")
            
            if classified_type == expected_type:
                print("   ✅ CORRECT")
                correct += 1
            else:
                print("   ❌ INCORRECT")
                
            results.append({
                'query': query,
                'expected': expected_type,
                'classified': classified_type,
                'translated': translated_query,
                'correct': classified_type == expected_type
            })
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results.append({
                'query': query,
                'expected': expected_type,
                'classified': 'error',
                'translated': query,
                'error': str(e),
                'correct': False
            })
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 CLASSIFICATION RESULTS")
    print(f"Accuracy: {correct}/{total} ({correct/total*100:.1f}%)")
    
    # Show breakdown by category
    categories = {}
    for result in results:
        category = result['expected']
        if category not in categories:
            categories[category] = {'correct': 0, 'total': 0}
        categories[category]['total'] += 1
        if result['correct']:
            categories[category]['correct'] += 1
    
    print("\nBreakdown by category:")
    for category, stats in categories.items():
        accuracy = stats['correct'] / stats['total'] * 100
        print(f"  {category}: {stats['correct']}/{stats['total']} ({accuracy:.1f}%)")
    
    return results, categories

def test_full_chat():
    """Test a few full chat examples"""
    
    print("\n🗨️  Testing Full Chat Examples")
    print("=" * 60)
    
    crew = SnlPoc()
    
    test_cases = [
        "Van Gogh exhibition posters in Switzerland",
        "Tell me about Bur's thesis on visual attention",
        "Find books about van gogh",
        "at what time the library opens?",
    ]
    
    chat_results = []
    
    for query in test_cases:
        print(f"\n💬 Query: '{query}'")
        print("-" * 40)
        
        try:
            # Get classification first
            translated_query, query_type = crew._translate_and_classify(query)
            
            # Get full response
            response = crew.chat(query)
            print(f"Response: {response[:200]}...")
            
            chat_results.append({
                'query': query,
                'translated_query': translated_query,
                'classified_type': query_type,
                'response': response,
                'success': True
            })
            
        except Exception as e:
            print(f"❌ Error: {e}")
            chat_results.append({
                'query': query,
                'translated_query': None,
                'classified_type': None,
                'response': None,
                'error': str(e),
                'success': False
            })
    
    return chat_results

def save_results_to_file(classification_results, categories, chat_results):
    """Save all test results to a formatted file"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"output/test_results_{timestamp}.txt"
    
    # Ensure output directory exists
    os.makedirs("output", exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("4-WAY CLASSIFICATION SYSTEM TEST RESULTS\n")
        f.write("=" * 80 + "\n")
        f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Classification Results
        f.write("📊 CLASSIFICATION TEST RESULTS\n")
        f.write("-" * 50 + "\n")
        
        correct_total = sum(1 for r in classification_results if r['correct'])
        total = len(classification_results)
        f.write(f"Overall Accuracy: {correct_total}/{total} ({correct_total/total*100:.1f}%)\n\n")
        
        # Category breakdown
        f.write("Accuracy by Category:\n")
        for category, stats in categories.items():
            accuracy = stats['correct'] / stats['total'] * 100
            f.write(f"  {category.upper()}: {stats['correct']}/{stats['total']} ({accuracy:.1f}%)\n")
        f.write("\n")
        
        # Detailed classification results
        f.write("DETAILED CLASSIFICATION RESULTS:\n")
        f.write("-" * 50 + "\n")
        
        for i, result in enumerate(classification_results, 1):
            f.write(f"{i}. Query: '{result['query']}'\n")
            f.write(f"   Expected Type: {result['expected']}\n")
            f.write(f"   Classified As: {result['classified']}\n")
            f.write(f"   Translated: '{result['translated']}'\n")
            f.write(f"   Result: {'✅ CORRECT' if result['correct'] else '❌ INCORRECT'}\n")
            if 'error' in result:
                f.write(f"   Error: {result['error']}\n")
            f.write("\n")
        
        # Chat Results
        f.write("\n" + "=" * 80 + "\n")
        f.write("🗨️  FULL CHAT TEST RESULTS\n")
        f.write("=" * 80 + "\n\n")
        
        for i, result in enumerate(chat_results, 1):
            f.write(f"TEST {i}\n")
            f.write("-" * 30 + "\n")
            f.write(f"Query: '{result['query']}'\n")
            
            if result['success']:
                f.write(f"Translated: '{result['translated_query']}'\n")
                f.write(f"Classified Type: {result['classified_type']}\n")
                f.write(f"Response:\n{result['response']}\n")
            else:
                f.write(f"❌ ERROR: {result['error']}\n")
            
            f.write("\n" + "-" * 30 + "\n\n")
        
        # JSON export for programmatic access
        f.write("\n" + "=" * 80 + "\n")
        f.write("📄 RAW DATA (JSON FORMAT)\n")
        f.write("=" * 80 + "\n")
        
        export_data = {
            'timestamp': timestamp,
            'classification_results': classification_results,
            'category_stats': categories,
            'chat_results': chat_results,
            'summary': {
                'classification_accuracy': correct_total/total*100,
                'total_tests': total,
                'correct_classifications': correct_total
            }
        }
        
        f.write(json.dumps(export_data, indent=2, ensure_ascii=False))
    
    return filename

if __name__ == "__main__":
    print("🚀 Starting Classification System Tests")
    
    # Test classification accuracy
    classification_results, categories = test_classification()
    
    # Test full chat functionality
    chat_results = test_full_chat()
    
    # Save all results to file
    output_file = save_results_to_file(classification_results, categories, chat_results)
    
    print(f"\n📁 Results saved to: {output_file}")
    print("✅ Testing complete!") 