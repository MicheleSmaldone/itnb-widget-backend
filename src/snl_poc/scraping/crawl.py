import requests
from bs4 import BeautifulSoup
import json
import os
from urllib.parse import urljoin, urlparse

def crawl_site(start_urls, base_url, max_pages=100):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    })
    visited = set()
    to_visit = list(start_urls)
    results = []
    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue
        print(f"Crawling: {url}")
        try:
            resp = session.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, 'html.parser')
            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            headings = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])]
            results.append({
                "url": url,
                "title": title,
                "headings": headings
            })
            for a in soup.find_all('a', href=True):
                link = a['href']
                abs_link = urljoin(url, link)
                if urlparse(abs_link).netloc == urlparse(base_url).netloc and abs_link not in visited and abs_link not in to_visit:
                    if "/en/" in abs_link:
                        to_visit.append(abs_link)
        except Exception as e:
            print(f"Failed to crawl {url}: {e}")
        visited.add(url)
    output_dir = "../output"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "snl_crawl_summary.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Crawl summary saved to {output_file}")
    return results

def main():
    base_url = "https://www.nb.admin.ch"
    start_urls = [
        f"{base_url}/snl/en/home.html",
        f"{base_url}/snl/en/home/services/user-services.html"
    ]
    crawl_site(start_urls, base_url, max_pages=50)

if __name__ == "__main__":
    main() 