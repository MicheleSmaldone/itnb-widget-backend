#!/usr/bin/env python3

import os
import sys
import logging
from pathlib import Path

# Add the tools directory to Python path so we can import the GroundX tool
tools_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tools')
sys.path.insert(0, tools_dir)

from groundx_tool import GroundXTool

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PhoenixGroundXIngester(GroundXTool):
    """Custom GroundX tool configured for Phoenix Technologies data ingestion"""
    
    def __init__(self):
        # Set knowledge directory to the Phoenix data location
        knowledge_dir = "/app/src/snl_poc/knowledge"
        
        # Initialize with custom settings - we'll override the bucket setup
        super().__init__(
            bucket_name="phoenix",
            knowledge_dir=knowledge_dir,
            max_chunks=4
        )
        
        # Override the bucket ID to use the existing one
        self._bucket_id = 20768
        logger.info(f"Using existing bucket ID: {self._bucket_id}")
        
        # Clear the ingested files tracking since we're using an existing bucket
        self._ingested_files = {}
        
        # Get existing documents in the bucket
        self._get_existing_documents()
    
    def _setup_bucket(self) -> int:
        """Override to use existing bucket ID instead of creating new one"""
        logger.info(f"Using existing bucket 'phoenix' with ID 20768")
        return 20768
    
    def ingest_phoenix_data(self) -> bool:
        """Ingest all Phoenix Technologies JSON files"""
        try:
            knowledge_path = Path(self._knowledge_dir)
            if not knowledge_path.exists():
                logger.error(f"Knowledge directory not found: {self._knowledge_dir}")
                return False
            
            logger.info(f"Starting ingestion of Phoenix Technologies data from {self._knowledge_dir}")
            logger.info(f"Target bucket ID: {self._bucket_id}")
            
            # Find all JSON files
            json_files = list(knowledge_path.glob("*.json"))
            logger.info(f"Found {len(json_files)} JSON files to process")
            
            if not json_files:
                logger.warning("No JSON files found in knowledge directory")
                return False
            
            # List files to be processed
            for json_file in json_files:
                logger.info(f"  - {json_file.name} ({json_file.stat().st_size / 1024:.1f} KB)")
            
            # Use the parent class ingestion method
            success = self.ingest_documents()
            
            if success:
                logger.info("✅ Phoenix Technologies data ingestion completed successfully!")
            else:
                logger.error("❌ Phoenix Technologies data ingestion failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Error during Phoenix data ingestion: {str(e)}")
            return False

def main():
    """Main function to ingest Phoenix Technologies data"""
    try:
        logger.info("🚀 Starting Phoenix Technologies data ingestion to GroundX")
        
        # Check if GROUNDX_API_KEY is set
        if not os.getenv("GROUNDX_API_KEY"):
            logger.error("GROUNDX_API_KEY environment variable not set")
            return False
        
        # Create ingester
        ingester = PhoenixGroundXIngester()
        
        # Handle command line arguments
        if len(sys.argv) > 1:
            if sys.argv[1] == "--clear":
                logger.info("🗑️ Clearing existing documents from bucket...")
                success = ingester.clear_bucket()
                if success:
                    logger.info("✅ Bucket cleared successfully")
                else:
                    logger.error("❌ Failed to clear bucket")
                return success
            elif sys.argv[1] == "--status":
                logger.info("📊 Checking bucket status...")
                ingester._get_existing_documents()
                logger.info(f"Bucket contains {len(ingester._ingested_files)} existing documents")
                for filename in ingester._ingested_files.keys():
                    logger.info(f"  - {filename}")
                return True
        
        # Perform ingestion
        success = ingester.ingest_phoenix_data()
        
        if success:
            logger.info("🎉 All Phoenix Technologies data has been successfully ingested into GroundX!")
            logger.info(f"📁 Bucket ID: {ingester._bucket_id}")
            logger.info(f"📊 You can now query this data using the GroundX search functionality")
        else:
            logger.error("💥 Ingestion process failed. Check the logs above for details.")
        
        return success
        
    except Exception as e:
        logger.error(f"💥 Critical error: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
