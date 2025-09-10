#!/usr/bin/env python
import os
import json
import textwrap
from dotenv import load_dotenv
from groundx import GroundX


def ensure_env_defaults() -> None:
    """Ensure GroundX env vars are set with sane defaults for on-prem."""
    if not os.getenv("GROUNDX_API_KEY"):
        os.environ["GROUNDX_API_KEY"] = "5c49be10-d228-4dd8-bbb0-d59300698ef6"
    if not os.getenv("GROUNDX_BASE_URL"):
        os.environ["GROUNDX_BASE_URL"] = "https://groundx-service-eyelevel.apps.eyelevel.kvant.cloud/api"


def print_result_chunks(search_response) -> None:
    search = getattr(search_response, "search", None)
    results = getattr(search, "results", []) if search else []
    print(f"Total results: {len(results)}")

    for idx, result in enumerate(results, start=1):
        text = getattr(result, "text", "")
        print(f"\n=== RESULT {idx} | length={len(text)} chars ===")
        # Show up to 4000 chars of the raw chunk
        print(text[:4000])

        # Try to parse as JSON and extract any team_info image URLs
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                keys_preview = list(data.keys())
                print(f"JSON keys: {keys_preview}")
                if "team_info" in data and isinstance(data["team_info"], list):
                    print("Team members and images found in chunk:")
                    for member in data["team_info"]:
                        try:
                            name = member.get("name")
                            img = member.get("image")
                            print(f"- {name}: {img}")
                        except Exception:
                            continue
        except Exception as e:
            print(f"(Not JSON or parse error: {e})")


def main() -> None:
    load_dotenv()
    ensure_env_defaults()

    api_key = os.environ["GROUNDX_API_KEY"]
    base_url = os.environ.get("GROUNDX_BASE_URL")

    print(f"Using GroundX base: {base_url}")
    gx = GroundX(api_key=api_key, base_url=base_url)

    bucket_id = int(os.getenv("GROUNDX_BUCKET_ID", "69"))
    query = os.getenv("GROUNDX_TEST_QUERY", "who is nicolai brignoli?")

    print(f"Bucket: {bucket_id}")
    print(f"Query: {query}")

    resp = gx.search.content(id=bucket_id, query=query, verbosity=2, n=5)
    print_result_chunks(resp)


if __name__ == "__main__":
    main()


