#!/usr/bin/env python3

import json
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def remove_technical_specs_from_file(file_path: Path) -> bool:
    """Remove technical_specs field from a single JSON file"""
    try:
        logger.info(f"Processing: {file_path.name}")
        
        # Load the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Track if we made any changes
        changes_made = False
        
        # Check if it's a single object with technical_specs
        if isinstance(data, dict) and 'technical_specs' in data:
            del data['technical_specs']
            changes_made = True
            logger.info(f"  - Removed technical_specs from root object")
        
        # Check if it's the combined format with pages array
        if isinstance(data, dict) and 'pages' in data:
            pages = data.get('pages', [])
            for i, page in enumerate(pages):
                if isinstance(page, dict) and 'technical_specs' in page:
                    del page['technical_specs']
                    changes_made = True
                    logger.info(f"  - Removed technical_specs from page {i+1}")
        
        # If it's directly a list of pages
        if isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, dict) and 'technical_specs' in item:
                    del item['technical_specs']
                    changes_made = True
                    logger.info(f"  - Removed technical_specs from item {i+1}")
        
        # Save the file back if changes were made
        if changes_made:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"  ✅ Updated {file_path.name}")
        else:
            logger.info(f"  - No technical_specs field found in {file_path.name}")
        
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Error processing {file_path.name}: {str(e)}")
        return False

def clean_all_json_files(scrape_out_dir: Path) -> bool:
    """Remove technical_specs field from all JSON files in the directory"""
    try:
        if not scrape_out_dir.exists():
            logger.error(f"Directory not found: {scrape_out_dir}")
            return False
        
        # Find all JSON files
        json_files = list(scrape_out_dir.glob("*.json"))
        
        if not json_files:
            logger.warning("No JSON files found in scrape_out directory")
            return False
        
        logger.info(f"Found {len(json_files)} JSON files to process")
        
        # Process each file
        success_count = 0
        for json_file in json_files:
            if remove_technical_specs_from_file(json_file):
                success_count += 1
        
        logger.info(f"✅ Successfully processed {success_count}/{len(json_files)} files")
        return success_count == len(json_files)
        
    except Exception as e:
        logger.error(f"❌ Error cleaning JSON files: {str(e)}")
        return False

def main():
    """Main function to clean technical_specs from all JSON files"""
    try:
        logger.info("🧹 Starting cleanup of technical_specs fields from ITNB JSON files")
        
        # Get the scrape_out directory
        script_dir = Path(__file__).parent
        scrape_out_dir = script_dir / "scrape_out"
        
        logger.info(f"Target directory: {scrape_out_dir}")
        
        # Create backup warning
        logger.warning("⚠️  This script will modify JSON files in place.")
        logger.warning("⚠️  Make sure you have backups if needed.")
        
        # Ask for confirmation if running interactively
        import sys
        if sys.stdin.isatty():
            response = input("Do you want to continue? (y/N): ")
            if response.lower() != 'y':
                logger.info("Operation cancelled by user")
                return False
        
        # Clean all files
        success = clean_all_json_files(scrape_out_dir)
        
        if success:
            logger.info("🎉 Cleanup completed successfully!")
            logger.info("All technical_specs fields have been removed from JSON files")
        else:
            logger.error("💥 Cleanup failed or completed with errors")
        
        return success
        
    except Exception as e:
        logger.error(f"💥 Critical error: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
