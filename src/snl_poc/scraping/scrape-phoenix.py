import requests
from bs4 import BeautifulSoup, Tag
import json
import time
import os
from typing import Dict, List, Any
import re
from urllib.parse import urljoin

class PhoenixScraper:
    def __init__(self):
        self.base_url = "https://phoenix-technologies.ch"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.local_dir = os.path.join(os.path.dirname(__file__), 'scrape_out')
        os.makedirs(self.local_dir, exist_ok=True)
    
    def get_soup(self, url: str) -> BeautifulSoup:
        """Download and parse HTML from URL"""
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            html = resp.text
            print(f"Downloaded: {url}")
            time.sleep(1)  # Be polite
            return BeautifulSoup(html, 'html.parser')
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return BeautifulSoup("", 'html.parser')

    def extract_common_elements(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract common elements present on all pages"""
        data = {
            "url": url,
            "title": soup.title.string.strip() if soup.title and soup.title.string else "",
            "meta_description": "",
            "headings": [],
            "main_content": "",
            "call_to_actions": [],
            "contact_info": {},
            "navigation": []
        }
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            data["meta_description"] = meta_desc.get('content', '')
        
        # Headings hierarchy
        for level in ['h1', 'h2', 'h3', 'h4']:
            headings = soup.find_all(level)
            for h in headings:
                data["headings"].append({
                    "level": level,
                    "text": h.get_text(strip=True)
                })
        
        # Main content - look for main content areas
        main_content_parts = []
        for container in soup.find_all(['main', 'article', 'section']):
            # Skip navigation and header/footer sections
            if not any(cls in str(container.get('class', [])).lower() 
                      for cls in ['nav', 'header', 'footer', 'menu']):
                content = container.get_text(separator=' ', strip=True)
                if content and len(content) > 100:  # Only substantial content
                    main_content_parts.append(content)
        
        data["main_content"] = ' '.join(main_content_parts)
        
        # Call-to-action buttons and links
        cta_selectors = [
            'a[class*="btn"]', 'a[class*="button"]', 
            'a[href*="contact"]', 'a[href*="buy"]', 
            'a[href*="learn"]', 'a[href*="chat"]'
        ]
        
        for selector in cta_selectors:
            ctas = soup.select(selector)
            for cta in ctas:
                if isinstance(cta, Tag):
                    data["call_to_actions"].append({
                        "text": cta.get_text(strip=True),
                        "href": cta.get('href', ''),
                        "full_url": urljoin(url, cta.get('href', ''))
                    })
        
        # Contact information
        contact_links = soup.find_all('a', href=True)
        for link in contact_links:
            href = link.get('href', '')
            if href.startswith('mailto:'):
                data["contact_info"]["email"] = href.replace('mailto:', '')
            elif href.startswith('tel:'):
                data["contact_info"]["phone"] = href.replace('tel:', '')
        
        return data

    def scrape_homepage(self, url: str) -> Dict[str, Any]:
        """Extract homepage-specific content"""
        soup = self.get_soup(url)
        data = self.extract_common_elements(soup, url)
        
        # Main value proposition
        hero_section = soup.find(['section', 'div'], class_=lambda x: x and 'hero' in str(x).lower())
        if hero_section:
            data["value_proposition"] = hero_section.get_text(separator=' ', strip=True)
        
        # Service/product highlights from homepage
        services = []
        service_sections = soup.find_all(['section', 'div'], class_=lambda x: x and any(
            keyword in str(x).lower() for keyword in ['service', 'product', 'solution']
        ))
        
        for section in service_sections:
            if isinstance(section, Tag):
                title_elem = section.find(['h1', 'h2', 'h3'])
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    description = section.get_text(separator=' ', strip=True)
                    services.append({
                        "title": title,
                        "description": description[:500]  # Truncate long descriptions
                    })
        
        data["featured_services"] = services
        data["page_type"] = "homepage"
        return data

    def scrape_product_service(self, url: str) -> Dict[str, Any]:
        """Extract product/service page content"""
        soup = self.get_soup(url)
        data = self.extract_common_elements(soup, url)
        
        # Product/service specific details
        product_info = {
            "features": [],
            "benefits": [],
            "technical_specs": [],
            "pricing_info": "",
            "use_cases": []
        }
        
        # Look for feature lists
        feature_lists = soup.find_all(['ul', 'ol'])
        for ul in feature_lists:
            parent_heading = ul.find_previous(['h1', 'h2', 'h3', 'h4'])
            if parent_heading and any(keyword in parent_heading.get_text().lower() 
                                    for keyword in ['feature', 'benefit', 'capability']):
                for li in ul.find_all('li'):
                    feature_text = li.get_text(strip=True)
                    if feature_text:
                        if 'feature' in parent_heading.get_text().lower():
                            product_info["features"].append(feature_text)
                        elif 'benefit' in parent_heading.get_text().lower():
                            product_info["benefits"].append(feature_text)
        
        # Look for technical specifications
        spec_sections = soup.find_all(string=lambda text: text and any(
            keyword in text.lower() for keyword in ['specification', 'requirement', 'technical']
        ))
        for spec_text in spec_sections:
            parent = spec_text.parent if hasattr(spec_text, 'parent') else None
            if parent:
                content = parent.get_text(strip=True)
                if content and len(content) > 20:
                    product_info["technical_specs"].append(content)
        
        # Extract pricing mentions
        pricing_text = soup.find_all(string=lambda text: text and any(
            keyword in text.lower() for keyword in ['price', 'cost', 'pricing', 'fee', '$', 'chf', 'eur']
        ))
        if pricing_text:
            product_info["pricing_info"] = ' '.join([str(p).strip() for p in pricing_text[:3]])
        
        data.update(product_info)
        data["page_type"] = "product_service"
        return data

    def scrape_solution(self, url: str) -> Dict[str, Any]:
        """Extract solution page content"""
        soup = self.get_soup(url)
        data = self.extract_common_elements(soup, url)
        
        solution_info = {
            "industry": "",
            "use_case": "",
            "challenges_addressed": [],
            "solution_approach": "",
            "outcomes": []
        }
        
        # Determine if it's an industry or use case solution
        if '/industries/' in url:
            solution_info["industry"] = url.split('/industries/')[-1].replace('-', ' ').title()
        elif '/use-cases/' in url:
            solution_info["use_case"] = url.split('/use-cases/')[-1].replace('-', ' ').title()
        
        # Look for challenge sections
        challenge_sections = soup.find_all(['h2', 'h3'], string=lambda text: text and any(
            keyword in text.lower() for keyword in ['challenge', 'problem', 'issue', 'pain']
        ))
        for section in challenge_sections:
            next_content = section.find_next(['p', 'ul', 'div'])
            if next_content:
                solution_info["challenges_addressed"].append(next_content.get_text(strip=True))
        
        # Look for solution approach
        solution_sections = soup.find_all(['h2', 'h3'], string=lambda text: text and any(
            keyword in text.lower() for keyword in ['solution', 'approach', 'how we']
        ))
        for section in solution_sections:
            next_content = section.find_next(['p', 'div'])
            if next_content:
                solution_info["solution_approach"] = next_content.get_text(strip=True)
        
        # Look for outcomes/results
        outcome_sections = soup.find_all(['h2', 'h3'], string=lambda text: text and any(
            keyword in text.lower() for keyword in ['outcome', 'result', 'benefit', 'impact']
        ))
        for section in outcome_sections:
            next_content = section.find_next(['p', 'ul'])
            if next_content:
                if next_content.name == 'ul':
                    outcomes = [li.get_text(strip=True) for li in next_content.find_all('li')]
                    solution_info["outcomes"].extend(outcomes)
                else:
                    solution_info["outcomes"].append(next_content.get_text(strip=True))
        
        data.update(solution_info)
        data["page_type"] = "solution"
        return data

    def scrape_company(self, url: str) -> Dict[str, Any]:
        """Extract company page content"""
        soup = self.get_soup(url)
        data = self.extract_common_elements(soup, url)
        
        company_info = {
            "company_description": "",
            "mission_vision": "",
            "team_info": [],
            "certifications": [],
            "careers": [],
            "contact_details": {}
        }
        
        # Company description
        about_sections = soup.find_all(['p', 'div'], string=lambda text: text and len(str(text)) > 100)
        if about_sections:
            company_info["company_description"] = about_sections[0].get_text(strip=True)
        
        # Mission/vision statements
        mission_keywords = ['mission', 'vision', 'values', 'commitment']
        for keyword in mission_keywords:
            mission_heading = soup.find(['h1', 'h2', 'h3'], string=lambda text: text and keyword in text.lower())
            if mission_heading:
                next_content = mission_heading.find_next(['p', 'div'])
                if next_content:
                    company_info["mission_vision"] = next_content.get_text(strip=True)
                    break
        
        # Team information (if on team page)
        if '/team' in url:
            team_members = soup.find_all(['div', 'section'], class_=lambda x: x and 'team' in str(x).lower())
            for member_section in team_members:
                name_elem = member_section.find(['h3', 'h4', 'h5'])
                if name_elem:
                    name = name_elem.get_text(strip=True)
                    title = ""
                    title_elem = name_elem.find_next(['p', 'span', 'div'])
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                    company_info["team_info"].append({"name": name, "title": title})
        
        # Certifications (if on certificates page)
        if '/certificates' in url or '/compliance' in url:
            cert_text = soup.get_text()
            cert_keywords = ['ISO', 'certified', 'compliance', 'standard', 'audit']
            for keyword in cert_keywords:
                if keyword in cert_text:
                    # Find surrounding context
                    cert_sections = soup.find_all(string=lambda text: text and keyword in str(text))
                    for cert in cert_sections[:5]:  # Limit to first 5 matches
                        if hasattr(cert, 'parent'):
                            company_info["certifications"].append(cert.parent.get_text(strip=True))
        
        # Contact details (if on contact page)
        if '/contact' in url:
            address_blocks = soup.find_all(['div', 'section'], class_=lambda x: x and 'address' in str(x).lower())
            for block in address_blocks:
                company_info["contact_details"]["address"] = block.get_text(strip=True)
        
        data.update(company_info)
        data["page_type"] = "company"
        return data

    def scrape_partner(self, url: str) -> Dict[str, Any]:
        """Extract partner/ecosystem page content"""
        soup = self.get_soup(url)
        data = self.extract_common_elements(soup, url)
        
        partner_info = {
            "partner_types": [],
            "partner_list": [],
            "partnership_benefits": [],
            "success_stories": []
        }
        
        # Partner categories
        partner_headings = soup.find_all(['h2', 'h3'], string=lambda text: text and 'partner' in text.lower())
        for heading in partner_headings:
            partner_info["partner_types"].append(heading.get_text(strip=True))
        
        # Individual partners (look for logos or names)
        partner_sections = soup.find_all(['div', 'section'], class_=lambda x: x and 'partner' in str(x).lower())
        for section in partner_sections:
            partner_names = section.find_all(['img', 'h4', 'h5'])
            for name_elem in partner_names:
                if name_elem.name == 'img':
                    alt_text = name_elem.get('alt', '')
                    if alt_text:
                        partner_info["partner_list"].append(alt_text)
                else:
                    partner_info["partner_list"].append(name_elem.get_text(strip=True))
        
        # Success stories (if on success stories page)
        if '/success-stories' in url:
            story_sections = soup.find_all(['div', 'article'], class_=lambda x: x and 'story' in str(x).lower())
            for story in story_sections:
                story_title = story.find(['h2', 'h3', 'h4'])
                if story_title:
                    story_content = story.get_text(strip=True)
                    partner_info["success_stories"].append({
                        "title": story_title.get_text(strip=True),
                        "content": story_content[:500]  # Truncate
                    })
        
        data.update(partner_info)
        data["page_type"] = "partner"
        return data

    def scrape_news(self, url: str) -> Dict[str, Any]:
        """Extract news page content"""
        soup = self.get_soup(url)
        data = self.extract_common_elements(soup, url)
        
        news_info = {
            "articles": [],
            "press_releases": [],
            "events": []
        }
        
        # News articles
        article_sections = soup.find_all(['article', 'div'], class_=lambda x: x and any(
            keyword in str(x).lower() for keyword in ['news', 'article', 'post']
        ))
        
        for article in article_sections:
            title_elem = article.find(['h1', 'h2', 'h3'])
            if title_elem:
                title = title_elem.get_text(strip=True)
                content = article.get_text(strip=True)
                date_elem = article.find(['time', 'span'], class_=lambda x: x and 'date' in str(x).lower())
                date = date_elem.get_text(strip=True) if date_elem else ""
                
                news_info["articles"].append({
                    "title": title,
                    "content": content[:300],  # Truncate
                    "date": date
                })
        
        data.update(news_info)
        data["page_type"] = "news"
        return data

    def scrape_page_by_type(self, url: str, page_type: str) -> Dict[str, Any]:
        """Route to appropriate scraper based on page type"""
        scraper_map = {
            "homepage": self.scrape_homepage,
            "product_service": self.scrape_product_service,
            "solution": self.scrape_solution,
            "company": self.scrape_company,
            "partner": self.scrape_partner,
            "news": self.scrape_news
        }
        
        scraper_func = scraper_map.get(page_type, self.extract_common_elements)
        
        if scraper_func == self.extract_common_elements:
            # Fallback for general pages
            soup = self.get_soup(url)
            data = self.extract_common_elements(soup, url)
            data["page_type"] = "general"
            return data
        else:
            return scraper_func(url)

def main():
    # Load the crawl results to get all URLs
    crawl_file = os.path.join(os.path.dirname(__file__), 'scrape_out', 'phoenix_urls.txt')
    
    if not os.path.exists(crawl_file):
        print(f"Please run crawl-phoenix.py first to generate {crawl_file}")
        return
    
    scraper = PhoenixScraper()
    
    # Read URLs and their types
    urls_to_scrape = []
    with open(crawl_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if ': ' in line:
                page_type, url = line.split(': ', 1)
                urls_to_scrape.append((page_type, url))
    
    print(f"Found {len(urls_to_scrape)} pages to scrape")
    
    # Scrape each page
    all_results = []
    for i, (page_type, url) in enumerate(urls_to_scrape):
        print(f"\nScraping {i+1}/{len(urls_to_scrape)}: {page_type} - {url}")
        try:
            result = scraper.scrape_page_by_type(url, page_type)
            all_results.append(result)
            
            # Save individual page result
            safe_filename = url.replace('https://phoenix-technologies.ch/en', '').replace('/', '_').strip('_')
            if not safe_filename:
                safe_filename = 'homepage'
            individual_file = os.path.join(scraper.local_dir, f"{safe_filename}_extracted.json")
            
            with open(individual_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
    
    # Save combined results
    combined_file = os.path.join(scraper.local_dir, "phoenix_all_content.json")
    with open(combined_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_pages": len(all_results),
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pages": all_results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\nScraping complete! Results saved to {combined_file}")
    print(f"Individual page files saved in {scraper.local_dir}")

if __name__ == "__main__":
    main()
