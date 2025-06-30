import requests
import os
import re

def extract_urls(filepath):
    urls = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            match = re.search(r'\[X\]\s*"(https?://[^"]+)"', line)
            if match:
                urls.append(match.group(1))
    return urls

def url_to_filename(url):
    # Use the last part of the path, or 'index' if root
    path = url.rstrip('/').split('/')
    name = path[-1] if path[-1] else 'index'
    # Remove query params and fragments
    name = name.split('?')[0].split('#')[0]
    if not name.endswith('.html'):
        name += '.html'
    return name

def download_and_save(url, out_dir):
    try:
        resp = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; DemoBot/1.0)'
        })
        resp.raise_for_status()
        filename = url_to_filename(url)
        out_path = os.path.join(out_dir, filename)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(resp.text)
        print(f"Saved {url} -> {out_path}")
    except Exception as e:
        print(f"Failed to download {url}: {e}")

def main():
    src = './scrape_out/selected_pages.txt'
    out_dir = './scrape_out'
    os.makedirs(out_dir, exist_ok=True)
    urls = extract_urls(src)
    for url in urls:
        download_and_save(url, out_dir)

if __name__ == '__main__':
    main() 