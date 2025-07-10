#!/usr/bin/env python3
"""
Ingest Van Gogh posters into GroundX
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.groundx_tool import GroundXTool

def main():
    print("🎨 Ingesting Van Gogh posters into GroundX...")
    
    try:
        # Initialize the GroundX tool
        tool = GroundXTool()
        
        # Check what files are in knowledge directory
        knowledge_dir = tool._knowledge_dir
        print(f"📁 Scanning knowledge directory: {knowledge_dir}")
        
        import os
        files = [f for f in os.listdir(knowledge_dir) if f.endswith('.json')]
        print(f"📄 Found JSON files: {files}")
        
        # Ingest documents
        success = tool.ingest_documents()
        
        if success:
            print("✅ Van Gogh posters successfully ingested!")
            print("🔍 You can now search for them using queries like:")
            print("   - 'Van Gogh exhibition posters'")
            print("   - 'Kunsthaus Zürich Van Gogh'") 
            print("   - 'Van Gogh Bern exhibition'")
        else:
            print("❌ Failed to ingest documents")
            
    except Exception as e:
        print(f"❌ Error during ingestion: {e}")

if __name__ == "__main__":
    main() 