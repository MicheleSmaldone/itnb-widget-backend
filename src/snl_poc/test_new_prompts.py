#!/usr/bin/env python3
"""
Test the updated book and poster prompts with new link formats
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crew import SnlPoc

def test_new_prompts():
    """Test the updated prompts for books and posters"""
    
    print("🧪 Testing Updated Book and Poster Prompts")
    print("=" * 50)
    
    # Initialize the crew
    crew = SnlPoc()
    
    # Test queries
    test_queries = [
        ("Find books by Van Gogh", "books"),
        ("Van Gogh exhibition posters", "posters"),
    ]
    
    for query, expected_type in test_queries:
        print(f"\n💬 Testing: '{query}'")
        print(f"Expected type: {expected_type}")
        print("-" * 40)
        
        try:
            # Get response
            response = crew.chat(query)
            
            print("Response:")
            print(response)
            
            # Check for expected link formats
            if expected_type == "books":
                if "[PRIMARY_SOURCE:" in response:
                    print("✅ Found PRIMARY_SOURCE link for books")
                else:
                    print("❌ Missing PRIMARY_SOURCE link for books")
                    
            elif expected_type == "posters":
                poster_page_found = "[POSTER_PAGE:" in response
                poster_image_found = "[POSTER_IMAGE:" in response
                
                if poster_page_found and poster_image_found:
                    print("✅ Found both POSTER_PAGE and POSTER_IMAGE links")
                elif poster_page_found:
                    print("⚠️ Found POSTER_PAGE but missing POSTER_IMAGE")
                elif poster_image_found:
                    print("⚠️ Found POSTER_IMAGE but missing POSTER_PAGE")
                else:
                    print("❌ Missing both poster link types")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n✅ Testing complete!")

if __name__ == "__main__":
    test_new_prompts() 