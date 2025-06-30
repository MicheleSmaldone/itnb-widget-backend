import requests
from bs4 import BeautifulSoup, Tag
import json
import time
import os
from typing import Dict, List, Any
import re

class SNLScraper:
    def __init__(self):
        self.base_url = "https://www.nb.admin.ch"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.local_dir = os.path.join(os.path.dirname(__file__), 'scrape_out')
    
    def url_to_local_filename(self, url: str) -> str:
        # Use the last part of the path, or 'index' if root
        path = url.rstrip('/').split('/')
        name = path[-1] if path[-1] else 'index'
        # Remove query params and fragments
        name = name.split('?')[0].split('#')[0]
        if not name.endswith('.html'):
            name += '.html'
        return name

    def get_soup(self, url: str) -> BeautifulSoup:
        """Try to load from local file, else download."""
        filename = self.url_to_local_filename(url)
        local_path = os.path.join(self.local_dir, filename)
        if os.path.exists(local_path):
            with open(local_path, 'r', encoding='utf-8') as f:
                html = f.read()
            print(f"Loaded local file: {local_path}")
        else:
            resp = self.session.get(url)
            resp.raise_for_status()
            html = resp.text
            print(f"Downloaded from web: {url}")
        return BeautifulSoup(html, 'html.parser')

    def scrape_home(self, url: str) -> Dict[str, Any]:
        soup = self.get_soup(url)
        data = {}
        # Example: extract opening hours from the sidebar
        opening_hours = None
        for h2 in soup.find_all('h2'):
            if 'Opening hours' in h2.get_text():
                # Look for the next <p> tag
                p = h2.find_next('p')
                if isinstance(p, Tag):
                    opening_hours = p.get_text(strip=True)
                    break
        data['opening_hours'] = opening_hours
        # Example: extract special notices
        special_notice = None
        for p in soup.find_all('p', class_='lead'):
            if isinstance(p, Tag):
                special_notice = p.get_text(strip=True)
                break
        data['special_notice'] = special_notice
        # Example: extract catalogues links
        catalogues = []
        for h2 in soup.find_all('h2'):
            if 'Catalogues' in h2.get_text():
                ul = h2.find_next('ul')
                if isinstance(ul, Tag):
                    for a in ul.find_all('a', href=True):
                        if isinstance(a, Tag) and a.has_attr('href'):
                            catalogues.append({
                                'text': a.get_text(strip=True),
                                'href': a['href']
                            })
        data['catalogues'] = catalogues
        # Example: extract main collection teasers
        collections = []
        for h2 in soup.find_all('h2'):
            if "Discover the National Library's collections" in h2.get_text():
                # Iterate over siblings until the next h2
                sibling = h2.next_sibling
                while sibling:
                    if isinstance(sibling, Tag) and sibling.name == 'h2':
                        break
                    if isinstance(sibling, Tag) and sibling.name == 'h3':
                        a = sibling.find('a')
                        if isinstance(a, Tag) and a.has_attr('href'):
                            collections.append({
                                'title': a.get_text(strip=True),
                                'href': a['href']
                            })
                    sibling = sibling.next_sibling
        data['collections'] = collections
        data['source_url'] = url
        return data

    def scrape_main_page(self) -> Dict[str, Any]:
        """Scrape the main homepage for general information"""
        url = f"{self.base_url}/snl/en/home.html"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            info = {
                "opening_hours": self._extract_opening_hours(soup),
                "exhibitions": self._extract_exhibitions(soup),
                "collections": self._extract_collections(soup),
                "contact_info": self._extract_contact_info(soup)
            }
            
            return info
        except Exception as e:
            print(f"Error scraping main page: {e}")
            return {}
    
    def scrape_user_services(self, url: str) -> Dict[str, Any]:
        soup = self.get_soup(url)
        data = {}
        # Extract all main service teasers
        services = []
        for teaser in soup.find_all('div', class_='mod-teaser'):
            title_tag = teaser.find('h3') if isinstance(teaser, Tag) else None
            link_tag = title_tag.find('a') if isinstance(title_tag, Tag) else None
            desc_tag = None
            if isinstance(teaser, Tag):
                for child in teaser.children:
                    if isinstance(child, Tag):
                        classes = child.get('class')
                        if isinstance(classes, list) and 'wrapper' in classes:
                            desc_tag = child
                            break
            desc_text = ''
            if isinstance(desc_tag, Tag):
                desc_text = desc_tag.get_text(strip=True)
            if isinstance(link_tag, Tag) and link_tag.has_attr('href'):
                services.append({
                    'title': link_tag.get_text(strip=True),
                    'href': link_tag['href'],
                    'description': desc_text
                })
        data['services'] = services
        data['source_url'] = url
        return data

    def _extract_opening_hours(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract opening hours information"""
        opening_hours = {}
        
        # Look for opening hours section
        hours_section = soup.find('h3', string=lambda text: text and 'Opening hours' in text)
        if hours_section:
            # Get the next sibling that contains the hours
            hours_text = hours_section.find_next_sibling()
            if hours_text:
                opening_hours["schedule"] = hours_text.get_text(strip=True)
        
        # Look for special notices
        special_notices = soup.find_all('p', string=lambda text: text and 'closed' in text.lower())
        if special_notices:
            opening_hours["special_notices"] = [notice.get_text(strip=True) for notice in special_notices]
        
        return opening_hours
    
    def _extract_exhibitions(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract current exhibitions"""
        exhibitions = []
        
        # Look for exhibition sections
        exhibition_sections = soup.find_all('h4', string=lambda text: text and 'exhibition' in text.lower())
        for section in exhibition_sections:
            exhibition = {}
            exhibition["title"] = section.get_text(strip=True)
            
            # Get description
            desc = section.find_next_sibling('p')
            if desc:
                exhibition["description"] = desc.get_text(strip=True)
            
            # Get dates
            dates = section.find_next_sibling(string=lambda text: text and any(month in text.lower() for month in ['july', 'august', 'september', 'october']))
            if dates:
                exhibition["dates"] = dates.strip()
            
            exhibitions.append(exhibition)
        
        return exhibitions
    
    def _extract_collections(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract information about collections"""
        collections = {}
        
        # Look for collection sections
        collection_sections = soup.find_all('h3', string=lambda text: text and 'collection' in text.lower())
        for section in collection_sections:
            title = section.get_text(strip=True)
            desc = section.find_next_sibling('p')
            if desc:
                collections[title] = desc.get_text(strip=True)
        
        return collections
    
    def _extract_contact_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract contact information"""
        contact = {}
        
        # Look for contact links
        contact_links = soup.find_all('a', href=lambda href: href and 'contact' in href)
        for link in contact_links:
            contact["contact_page"] = self.base_url + link.get('href')
        
        return contact
    
    def scrape_all_info(self) -> Dict[str, Any]:
        """Scrape all information from both pages"""
        print("Scraping main page...")
        main_info = self.scrape_main_page()
        time.sleep(5)  # Be polite
        
        print("Scraping user services page...")
        services_info = self.scrape_user_services()
        
        all_info = {
            "main_page": main_info,
            "user_services": services_info,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return all_info

    def scrape_contact(self, url: str) -> Dict[str, Any]:
        soup = self.get_soup(url)
        data = {}
        # Extract main address block
        address_block = soup.find('div', class_='mod-address')
        if address_block:
            address_text = address_block.get_text(separator=' ', strip=True)
            data['main_address'] = address_text
        # Extract all contact emails and phones
        emails = []
        phones = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('mailto:'):
                emails.append(href.replace('mailto:', ''))
            if href.startswith('tel:'):
                phones.append(href.replace('tel:', ''))
        data['emails'] = list(set(emails))
        data['phones'] = list(set(phones))
        # Extract department contacts (Prints and Drawings, Literary Archives)
        departments = []
        for div in soup.find_all('div', class_='mod-address'):
            dept = div.get_text(separator=' ', strip=True)
            if dept and dept not in data.get('main_address', ''):
                departments.append(dept)
        data['departments'] = departments
        # Extract links to forms, suggestions, etc.
        links = []
        for div in soup.find_all('div', class_='mod-link'):
            a = div.find('a', href=True)
            if a:
                links.append({'text': a.get_text(strip=True), 'href': a['href']})
        data['links'] = links
        data['source_url'] = url
        return data

    def scrape_opening_hours(self, url: str) -> Dict[str, Any]:
        soup = self.get_soup(url)
        data = {}
        # Extract special notice (alert box)
        specialbox = soup.find('div', class_='specialbox')
        if specialbox:
            alert = specialbox.get_text(separator=' ', strip=True)
            data['special_notice'] = alert
        # Extract opening hours table
        table = soup.find('table')
        hours = []
        if table:
            for row in table.find_all('tr'):
                cols = row.find_all(['td', 'th'])
                if len(cols) == 2:
                    label = cols[0].get_text(strip=True)
                    value = cols[1].get_text(strip=True)
                    hours.append({'label': label, 'value': value})
        data['opening_hours'] = hours
        # Extract extraordinary closures
        closures = []
        for h2 in soup.find_all(['h2', 'h4']):
            if 'closure' in h2.get_text(strip=True).lower():
                # Get all <p> after this heading until next heading
                sibling = h2.find_next_sibling()
                while sibling and (not (sibling.name and sibling.name.startswith('h'))):
                    if sibling.name == 'p':
                        closures.append(sibling.get_text(strip=True))
                    sibling = sibling.find_next_sibling()
        data['extraordinary_closures'] = closures
        # Extract links to alerts and social media
        links = []
        for div in soup.find_all('div', class_='mod-link'):
            a = div.find('a', href=True)
            if a:
                links.append({'text': a.get_text(strip=True), 'href': a['href']})
        data['links'] = links
        data['source_url'] = url
        return data

    def scrape_library(self, url: str) -> Dict[str, Any]:
        soup = self.get_soup(url)
        data = {}
        # Extract main lead/intro text
        lead = ''
        lead_p = soup.find('p', class_='lead')
        if lead_p and hasattr(lead_p, 'get_text'):
            lead = lead_p.get_text(strip=True)
        data['lead'] = lead
        # Extract all paragraphs and lists about registration and borrowing
        content = []
        for article in soup.find_all('article'):
            if not hasattr(article, 'find_all'):
                continue
            for p in article.find_all('p'):
                if hasattr(p, 'get_text'):
                    content.append(p.get_text(strip=True))
            for ul in article.find_all('ul'):
                items = [li.get_text(strip=True) for li in ul.find_all('li') if hasattr(li, 'get_text')]
                if items:
                    content.append(items)
        data['content'] = content
        # Extract all links (with text and href)
        links = []
        for div in soup.find_all('div', class_='mod-link'):
            a = div.find('a') if hasattr(div, 'find') else None
            if a and hasattr(a, 'get_text') and a.has_attr('href'):
                links.append({'text': a.get_text(strip=True), 'href': a['href']})
        data['links'] = links
        # Extract all downloads (PDFs)
        downloads = []
        for div in soup.find_all('div', class_='mod-download'):
            a = div.find('a') if hasattr(div, 'find') else None
            if a and hasattr(a, 'get_text') and a.has_attr('href'):
                downloads.append({'text': a.get_text(strip=True), 'href': a['href']})
        data['downloads'] = downloads
        # Extract contact info (address, phone, email)
        contact = {}
        address_block = soup.find('div', class_='mod-address')
        if address_block and hasattr(address_block, 'get_text'):
            contact['address'] = address_block.get_text(separator=' ', strip=True)
            # Extract phone and email
            phones = []
            emails = []
            for a in address_block.find_all('a') if hasattr(address_block, 'find_all') else []:
                if a.has_attr('href'):
                    href = a['href']
                    if isinstance(href, str) and href.startswith('tel:'):
                        phones.append(href.replace('tel:', ''))
                    if isinstance(href, str) and href.startswith('mailto:'):
                        emails.append(href.replace('mailto:', ''))
            contact['phones'] = phones
            contact['emails'] = emails
        data['contact'] = contact
        data['source_url'] = url
        return data

def main():
    selected_file = os.path.join(os.path.dirname(__file__), 'scrape_out', 'selected_pages.txt')
    url_map = {}
    with open(selected_file, 'r', encoding='utf-8') as f:
        for line in f:
            match = re.search(r'"(https?://[^"]+)"', line)
            if match:
                url = match.group(1)
                filename = SNLScraper().url_to_local_filename(url)
                url_map[filename] = url
    scraper = SNLScraper()
    for filename, url in url_map.items():
        if filename == 'home.html':
            data = scraper.scrape_home(url)
        elif filename == 'contact.html':
            data = scraper.scrape_contact(url)
        elif filename == 'opening-hours.html':
            data = scraper.scrape_opening_hours(url)
        elif filename == 'user-services.html':
            data = scraper.scrape_user_services(url)
        elif filename == 'library.html':
            data = scraper.scrape_library(url)
        else:
            print(f"No extraction logic for {filename}, skipping.")
            continue
        out_json = os.path.join(scraper.local_dir, filename.replace('.html', '_extracted.json'))
        with open(out_json, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Extracted data for {filename} saved to {out_json}")

if __name__ == "__main__":
    main()
