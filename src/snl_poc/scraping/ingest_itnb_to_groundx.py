#!/usr/bin/env python3

import os
import sys
import logging
import json
import time
from pathlib import Path
from groundx import Groundx
from groundx.models import Document

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ITNBGroundXIngester:
    """GroundX ingester configured for ITNB website data"""
    
    def __init__(self, api_key: str, base_url: str, bucket_name: str = "itnb-website-widget"):
        """Initialize the ITNB GroundX ingester"""
        self.api_key = api_key
        self.base_url = base_url
        self.bucket_name = bucket_name
        self.bucket_id = None
        
        # Initialize GroundX client with on-prem configuration
        self.client = Groundx(
            api_key=api_key,
            base_url=base_url
        )
        
        # Set the data directory to ITNB scrape output
        self.data_dir = Path(__file__).parent / "scrape_out"
        
        logger.info(f"Initialized ITNB GroundX Ingester")
        logger.info(f"API Base URL: {base_url}")
        logger.info(f"Target Bucket: {bucket_name}")
        logger.info(f"Data Directory: {self.data_dir}")
    
    def setup_bucket(self) -> bool:
        """Create or get the ITNB bucket"""
        try:
            logger.info(f"Setting up bucket '{self.bucket_name}'...")
            
            # Try to create the bucket
            bucket_response = self.client.buckets.create(
                name=self.bucket_name
            )
            
            self.bucket_id = bucket_response.bucket.bucket_id
            logger.info(f"✅ Created new bucket '{self.bucket_name}' with ID: {self.bucket_id}")
            return True
            
        except Exception as e:
            # If bucket already exists, try to find it
            logger.info(f"Bucket might already exist, trying to find it: {str(e)}")
            try:
                # List existing buckets to find our bucket
                buckets_response = self.client.buckets.list()
                for bucket in buckets_response.buckets:
                    if bucket.name == self.bucket_name:
                        self.bucket_id = bucket.bucket_id
                        logger.info(f"✅ Found existing bucket '{self.bucket_name}' with ID: {self.bucket_id}")
                        return True
                
                logger.error(f"❌ Could not find or create bucket '{self.bucket_name}'")
                return False
                
            except Exception as e2:
                logger.error(f"❌ Error setting up bucket: {str(e2)}")
                return False
    
    def clear_bucket(self) -> bool:
        """Clear all documents from the bucket"""
        try:
            if not self.bucket_id:
                logger.error("Bucket ID not set. Please run setup_bucket() first.")
                return False
            
            logger.info(f"Clearing all documents from bucket {self.bucket_id}...")
            
            # Get all documents in the bucket
            documents_response = self.client.documents.list()
            bucket_docs = [doc for doc in documents_response.documents if doc.bucket_id == self.bucket_id]
            
            if not bucket_docs:
                logger.info("No documents found in bucket to clear")
                return True
            
            # Delete each document
            for doc in bucket_docs:
                self.client.documents.delete(document_id=doc.document_id)
                logger.info(f"Deleted document: {doc.file_name}")
            
            logger.info(f"✅ Cleared {len(bucket_docs)} documents from bucket")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error clearing bucket: {str(e)}")
            return False
    
    def get_bucket_status(self) -> dict:
        """Get status of documents in the bucket"""
        try:
            if not self.bucket_id:
                return {"error": "Bucket ID not set"}
            
            documents_response = self.client.documents.list()
            bucket_docs = [doc for doc in documents_response.documents if doc.bucket_id == self.bucket_id]
            
            status = {
                "bucket_id": self.bucket_id,
                "bucket_name": self.bucket_name,
                "total_documents": len(bucket_docs),
                "documents": [{"name": doc.file_name, "id": doc.document_id} for doc in bucket_docs]
            }
            
            return status
            
        except Exception as e:
            return {"error": str(e)}
    
    def prepare_itnb_documents(self) -> list:
        """Prepare ITNB JSON files for ingestion"""
        documents = []
        
        try:
            # Check if data directory exists
            if not self.data_dir.exists():
                logger.error(f"Data directory not found: {self.data_dir}")
                return documents
            
            # Find the main ITNB content file
            main_content_file = self.data_dir / "itnb_all_content.json"
            
            if main_content_file.exists():
                logger.info(f"Found main ITNB content file: {main_content_file}")
                documents.append(Document(
                    bucket_id=self.bucket_id,
                    file_name="itnb_all_content.json",
                    file_path=str(main_content_file),
                    file_type="json"
                ))
            
            # Find individual extracted files
            individual_files = list(self.data_dir.glob("*_extracted.json"))
            logger.info(f"Found {len(individual_files)} individual extracted files")
            
            for file_path in individual_files:
                documents.append(Document(
                    bucket_id=self.bucket_id,
                    file_name=file_path.name,
                    file_path=str(file_path),
                    file_type="json"
                ))
            
            logger.info(f"Prepared {len(documents)} documents for ingestion")
            return documents
            
        except Exception as e:
            logger.error(f"Error preparing documents: {str(e)}")
            return documents
    
    def ingest_documents(self) -> bool:
        """Ingest all ITNB documents into GroundX"""
        try:
            if not self.bucket_id:
                logger.error("Bucket not set up. Please run setup_bucket() first.")
                return False
            
            # Prepare documents
            documents = self.prepare_itnb_documents()
            
            if not documents:
                logger.warning("No documents found to ingest")
                return False
            
            logger.info(f"Starting ingestion of {len(documents)} ITNB documents...")
            
            # Ingest documents
            ingest_response = self.client.ingest(documents=documents)
            process_id = ingest_response.ingest.process_id
            
            logger.info(f"Ingestion started with process ID: {process_id}")
            
            # Wait for ingestion to complete
            logger.info("Waiting for ingestion to complete...")
            while True:
                status_response = self.client.documents.get_processing_status_by_id(
                    process_id=process_id
                )
                
                status = status_response.ingest.status
                logger.info(f"Ingestion status: {status}")
                
                if status == "complete":
                    logger.info("✅ Ingestion completed successfully!")
                    return True
                elif status == "cancelled":
                    logger.warning("⚠️ Ingestion was cancelled")
                    return False
                elif status == "error":
                    logger.error("❌ Error during ingestion")
                    return False
                
                # Wait before checking again
                time.sleep(3)
            
        except Exception as e:
            logger.error(f"❌ Error during ingestion: {str(e)}")
            return False
    
    def run_full_ingestion(self) -> bool:
        """Run the complete ingestion process"""
        try:
            # Setup bucket
            if not self.setup_bucket():
                return False
            
            # Ingest documents
            success = self.ingest_documents()
            
            if success:
                # Show final status
                status = self.get_bucket_status()
                logger.info(f"🎉 ITNB data ingestion completed!")
                logger.info(f"📁 Bucket: {status['bucket_name']} (ID: {status['bucket_id']})")
                logger.info(f"📊 Total documents: {status['total_documents']}")
                
            return success
            
        except Exception as e:
            logger.error(f"❌ Error in full ingestion: {str(e)}")
            return False

def main():
    """Main function to ingest ITNB data"""
    try:
        logger.info("🚀 Starting ITNB website data ingestion to GroundX")
        
        # Configuration
        api_key = os.getenv("GROUNDX_API_KEY", "5c49be10-d228-4dd8-bbb0-d59300698ef6")
        base_url = os.getenv("GROUNDX_BASE_URL", "https://groundx-service-eyelevel.apps.eyelevel.kvant.cloud/api")
        bucket_name = "itnb-website-widget"
        
        if not api_key:
            logger.error("GROUNDX_API_KEY not set")
            return False
        
        # Create ingester
        ingester = ITNBGroundXIngester(
            api_key=api_key,
            base_url=base_url,
            bucket_name=bucket_name
        )
        
        # Handle command line arguments
        if len(sys.argv) > 1:
            if sys.argv[1] == "--clear":
                logger.info("🗑️ Clearing existing documents from bucket...")
                if ingester.setup_bucket():
                    success = ingester.clear_bucket()
                    if success:
                        logger.info("✅ Bucket cleared successfully")
                    else:
                        logger.error("❌ Failed to clear bucket")
                    return success
                return False
                
            elif sys.argv[1] == "--status":
                logger.info("📊 Checking bucket status...")
                if ingester.setup_bucket():
                    status = ingester.get_bucket_status()
                    if "error" in status:
                        logger.error(f"Error getting status: {status['error']}")
                        return False
                    
                    logger.info(f"Bucket: {status['bucket_name']} (ID: {status['bucket_id']})")
                    logger.info(f"Total documents: {status['total_documents']}")
                    for doc in status['documents']:
                        logger.info(f"  - {doc['name']} (ID: {doc['id']})")
                    return True
                return False
        
        # Run full ingestion
        success = ingester.run_full_ingestion()
        
        if success:
            logger.info("🎉 All ITNB data has been successfully ingested into GroundX!")
            logger.info("📊 You can now query this data using the GroundX search functionality")
        else:
            logger.error("💥 Ingestion process failed. Check the logs above for details.")
        
        return success
        
    except Exception as e:
        logger.error(f"💥 Critical error: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
