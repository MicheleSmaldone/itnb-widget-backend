import json
import os
import re
from pathlib import Path

"""Clean up JSON files produced by the scraping pipeline.

The script performs the following steps on every *.json file inside
`scrape_out/` (located next to this script) and writes the cleaned
version with the same filename to `scrape_out_cleaned/`:

1. Remove the keys `headings` and `call_to_actions` entirely.
2. Recursively delete entries that are empty strings, empty lists, or
   empty dictionaries after cleaning.
3. Strip redundant or non-meaningful substrings from text fields (e.g. the
   repeated `Download  (undefined, 0 B)` artefacts found in some pages).

Run the script once the scraping step has finished:

    python clean_scrape_out.py
"""

# Directory layout ---------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent
INPUT_DIR = ROOT_DIR / "scrape_out"
OUTPUT_DIR = ROOT_DIR / "scrape_out_cleaned"
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Heuristics for removing non-meaningful pieces of text.
# Add additional patterns here if new artefacts show up in the data.
# ---------------------------------------------------------------------------
NON_MEANINGFUL_PATTERNS = [
    re.compile(r"Download\s*\(undefined, 0 B\)", re.IGNORECASE),
]

def _strip_noise(text: str) -> str:
    """Remove non-meaningful patterns and collapse whitespace."""
    if not text:
        return ""
    cleaned = text
    for pat in NON_MEANINGFUL_PATTERNS:
        cleaned = pat.sub("", cleaned)
    # Collapse consecutive whitespace characters
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def _clean(value):
    """Recursively clean a JSON value.

    Returns None for values that should be removed.
    """
    # Remove falsy primitives ------------------------------------------------
    if value is None:
        return None

    # -----------------------------------------------------------------------
    # Handle primitive types
    # -----------------------------------------------------------------------
    if isinstance(value, str):
        cleaned = _strip_noise(value)
        return cleaned or None  # remove if empty after stripping

    if isinstance(value, (int, float, bool)):
        return value

    # -----------------------------------------------------------------------
    # Handle lists
    # -----------------------------------------------------------------------
    if isinstance(value, list):
        cleaned_list = [_clean(item) for item in value]
        cleaned_list = [item for item in cleaned_list if item is not None]
        return cleaned_list or None

    # -----------------------------------------------------------------------
    # Handle dicts
    # -----------------------------------------------------------------------
    if isinstance(value, dict):
        cleaned_dict = {}
        for k, v in value.items():
            # Drop unwanted keys outright
            if k in {"headings", "call_to_actions"}:
                continue
            cleaned_val = _clean(v)
            if cleaned_val is not None:
                cleaned_dict[k] = cleaned_val
        return cleaned_dict or None

    # Unknown type – return as-is
    return value

def main():
    json_files = sorted(INPUT_DIR.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {INPUT_DIR}")
        return

    for fp in json_files:
        try:
            with fp.open("r", encoding="utf-8") as f:
                data = json.load(f)
            cleaned = _clean(data) or {}
            out_fp = OUTPUT_DIR / fp.name
            with out_fp.open("w", encoding="utf-8") as f:
                json.dump(cleaned, f, ensure_ascii=False, indent=2)
            print(f"✓ Cleaned {fp.name} -> {out_fp.relative_to(ROOT_DIR)}")
        except Exception as exc:
            print(f"✗ Failed to clean {fp}: {exc}")

if __name__ == "__main__":
    main()
