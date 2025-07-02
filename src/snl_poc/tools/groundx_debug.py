# /app/src/snl_poc/tools/groundx_debug.py

import os
from groundx import GroundX
from dotenv import load_dotenv
import random
import requests
import pprint

load_dotenv()

def inspect_xray(xray_url):
    print(f"\nInspecting X-Ray at: {xray_url}")
    response = requests.get(xray_url)
    xray_data = response.json()
    print("Top-level X-Ray fields:", list(xray_data.keys()))
    # Print a sample of the structure
    if 'documentPages' in xray_data and xray_data['documentPages']:
        print("\nSample page keys:", list(xray_data['documentPages'][0].keys()))
        if 'chunks' in xray_data['documentPages'][0]:
            print("\nSample chunk:")
            print(xray_data['documentPages'][0]['chunks'][0] if xray_data['documentPages'][0]['chunks'] else 'No chunks on first page')
    print("\nFull X-Ray JSON is available for further inspection.")
    deep_inspect_xray(xray_data)
    save_full_xray_inspection(xray_data, 'xray_inspection_output.txt')

def deep_inspect_xray(xray_data):
    print("\n--- Deep X-Ray Inspection ---")
    # Handle documentPages (for paginated docs)
    pages = xray_data.get('documentPages', [])
    if pages:
        print(f"Number of pages: {len(pages)}")
        total_chunks = 0
        for i, page in enumerate(pages):
            n_chunks = len(page.get('chunks', []))
            total_chunks += n_chunks
            print(f"Page {i+1}: {n_chunks} chunks")
        print(f"Total chunks: {total_chunks}")
        if pages and pages[0].get('chunks'):
            first_chunk = pages[0]['chunks'][0]
            print("\nFirst chunk keys:", list(first_chunk.keys()))
            content = first_chunk.get('text') or first_chunk.get('json') or str(first_chunk)
            if isinstance(content, str) and len(content) > 300:
                print("First chunk content (truncated):", content[:300] + '...')
            else:
                print("First chunk content:", content)
        # Save all chunk content to file
        with open('xray_full_chunks_output.txt', 'w', encoding='utf-8') as f:
            for i, page in enumerate(pages):
                for j, chunk in enumerate(page.get('chunks', [])):
                    f.write(f'Page {i+1} Chunk {j+1} keys: {list(chunk.keys())}\n')
                    content = chunk.get('text') or chunk.get('json') or str(chunk)
                    f.write(f'Content: {pprint.pformat(content) if not isinstance(content, str) else content}\n\n')
    # Handle top-level chunks (for JSON, CSV, etc.)
    elif 'chunks' in xray_data and xray_data['chunks']:
        print(f"Top-level chunks: {len(xray_data['chunks'])}")
        first_chunk = xray_data['chunks'][0]
        print("\nFirst chunk keys:", list(first_chunk.keys()))
        content = first_chunk.get('text') or first_chunk.get('json') or str(first_chunk)
        if isinstance(content, str) and len(content) > 300:
            print("First chunk content (truncated):", content[:300] + '...')
        else:
            print("First chunk content:", content)
        # Save all chunk content to file
        with open('xray_full_chunks_output.txt', 'w', encoding='utf-8') as f:
            for j, chunk in enumerate(xray_data['chunks']):
                f.write(f'Chunk {j+1} keys: {list(chunk.keys())}\n')
                content = chunk.get('text') or chunk.get('json') or str(chunk)
                f.write(f'Content: {pprint.pformat(content) if not isinstance(content, str) else content}\n\n')
    else:
        print("No pages or chunks found in X-Ray.")
    print("--- End Deep X-Ray Inspection ---\n")
    explain_llm_input(xray_data)

def explain_llm_input(xray_data):
    print("\n--- LLM Input Explanation ---")
    # For each chunk, show what would be passed to the LLM
    # Typical order: 'text', 'suggestedText', 'json' (as string)
    if 'documentPages' in xray_data and xray_data['documentPages']:
        for i, page in enumerate(xray_data['documentPages']):
            for j, chunk in enumerate(page.get('chunks', [])):
                llm_input = chunk.get('suggestedText') or chunk.get('text') or (pprint.pformat(chunk.get('json')) if chunk.get('json') else None)
                print(f'Page {i+1} Chunk {j+1} LLM input:')
                if llm_input:
                    print(llm_input[:500] + ('...' if len(llm_input) > 500 else ''))
                else:
                    print('  [No LLM input field found]')
    elif 'chunks' in xray_data and xray_data['chunks']:
        for j, chunk in enumerate(xray_data['chunks']):
            llm_input = chunk.get('suggestedText') or chunk.get('text') or (pprint.pformat(chunk.get('json')) if chunk.get('json') else None)
            print(f'Chunk {j+1} LLM input:')
            if llm_input:
                print(llm_input[:500] + ('...' if len(llm_input) > 500 else ''))
            else:
                print('  [No LLM input field found]')
    else:
        print('No chunks found for LLM input.')
    print("--- End LLM Input Explanation ---\n")

def save_full_xray_inspection(xray_data, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('--- X-Ray Full Inspection ---\n')
        f.write('Top-level fields: ' + ', '.join(xray_data.keys()) + '\n\n')
        # Handle documentPages (for paginated docs)
        pages = xray_data.get('documentPages', [])
        if pages:
            f.write(f'Number of pages: {len(pages)}\n')
            total_chunks = 0
            for i, page in enumerate(pages):
                n_chunks = len(page.get('chunks', []))
                total_chunks += n_chunks
                f.write(f'Page {i+1}: {n_chunks} chunks\n')
                for j, chunk in enumerate(page.get('chunks', [])):
                    f.write(f'  Chunk {j+1} keys: {list(chunk.keys())}\n')
                    content = chunk.get('suggestedText') or chunk.get('text') or chunk.get('json') or str(chunk)
                    if isinstance(content, str) and len(content) > 1000:
                        f.write(f'    Content (truncated): {content[:1000]}...\n')
                    else:
                        f.write(f'    Content: {pprint.pformat(content) if not isinstance(content, str) else content}\n')
            f.write(f'Total chunks: {total_chunks}\n')
        # Handle top-level chunks (for JSON, CSV, etc.)
        elif 'chunks' in xray_data and xray_data['chunks']:
            f.write(f'Top-level chunks: {len(xray_data["chunks"])}\n')
            for j, chunk in enumerate(xray_data['chunks']):
                f.write(f'  Chunk {j+1} keys: {list(chunk.keys())}\n')
                content = chunk.get('text') or chunk.get('json') or str(chunk)
                if isinstance(content, str) and len(content) > 1000:
                    f.write(f'    Content (truncated): {content[:1000]}...\n')
                else:
                    f.write(f'    Content: {pprint.pformat(content) if not isinstance(content, str) else content}\n')
        else:
            f.write('No pages or chunks found in X-Ray.\n')
        f.write('--- End X-Ray Full Inspection ---\n')

def main():
    api_key = os.getenv("GROUNDX_API_KEY")
    if not api_key:
        raise ValueError("GROUNDX_API_KEY not found in environment variables")
    client = GroundX(api_key=api_key)

    # List buckets
    buckets = client.buckets.list()
    print("Available Buckets:")
    for b in buckets.buckets:
        print(f"  {b.bucket_id}: {b.name}")

    # Hardcode the bucket_id since there is only one
    bucket_id = 19752

    # List documents in the bucket
    docs = client.documents.lookup(id=bucket_id)
    print("\nDocuments in bucket:")
    doc_map = {}
    for d in docs.documents:
        print(f"  {d.document_id}: {d.file_name}")
        doc_map[d.file_name] = d.document_id

    file_name = "library_extracted.json"
    doc_id = doc_map.get(file_name)
    if not doc_id:
        print(f"File '{file_name}' not found in bucket.")
        return

    # Fetch document details (try to get chunked content)
    doc_details = client.documents.get(document_id=doc_id)
    print(f"\nChunks for document {file_name}:")

    print(doc_details)
    # Try to get xray_url robustly
    xray_url = getattr(doc_details, 'xray_url', None)
    if not xray_url and hasattr(doc_details, '__dict__'):
        xray_url = doc_details.__dict__.get('xray_url')
    if not xray_url and hasattr(doc_details, 'document') and hasattr(doc_details.document, 'xray_url'):
        xray_url = getattr(doc_details.document, 'xray_url', None)
    if not xray_url:
        print("xray_url not found. Available attributes:")
        print(dir(doc_details))
        return
    inspect_xray(xray_url)

if __name__ == "__main__":
    main()