import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from typing import Dict, List, Optional


class WebScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def scrape_url(self, url: str) -> Optional[Dict]:
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            data = {
                'url': url,
                'title': self._extract_title(soup),
                'content': self._extract_content(soup),
                'links': self._extract_links(soup),
                'timestamp': datetime.now().isoformat()
            }
            
            return data
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None

    def _extract_title(self, soup: BeautifulSoup) -> str:
        title_tag = soup.find('title')
        return title_tag.get_text().strip() if title_tag else ''

    def _extract_content(self, soup: BeautifulSoup) -> str:
        paragraphs = soup.find_all('p')
        content = ' '.join([p.get_text().strip() for p in paragraphs])
        return content

    def _extract_links(self, soup: BeautifulSoup) -> List[str]:
        links = []
        for a in soup.find_all('a', href=True):
            links.append(a['href'])
        return links

    def batch_scrape(self, urls: List[str]) -> List[Dict]:
        results = []
        for url in urls:
            data = self.scrape_url(url)
            if data:
                results.append(data)
        return results
