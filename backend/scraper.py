import os
from pathlib import Path
from typing import List, Optional
import logging
import requests
from bs4 import BeautifulSoup
import html2text
from urllib.parse import urljoin, urlparse, urldefrag
import re
import time

import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebScraper:
    
    def __init__(self):
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def scrape_url(self, url: str, output_filename: Optional[str] = None) -> str:
        try:
            logger.info(f"Scraping URL: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            text = self.html_converter.handle(str(soup))
            
            if output_filename:
                output_path = config.RAW_DOCS_DIR / output_filename
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Scraped from: {url}\n\n")
                    f.write(text)
                logger.info(f"Saved scraped content to {output_path}")
            
            return text
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return ""
    
    def scrape_multiple_urls(self, urls: List[str], delay: float = 1.0):
        for i, url in enumerate(urls, 1):
            domain = urlparse(url).netloc
            filename = f"scraped_{domain}_{i}.txt"
            self.scrape_url(url, filename)
            
            if i < len(urls):
                time.sleep(delay)
    
    def scrape_mortgage_site(self, base_url: str, max_pages: int = 10):
        visited = set()
        to_visit = [base_url]
        scraped_count = 0
        parsed_base = urlparse(base_url)
        base_domain = parsed_base.netloc
        base_path = parsed_base.path if parsed_base.path else '/'
        if not base_path.endswith('/'):
            base_path = base_path + '/'
        web_dir = config.RAW_DOCS_DIR / 'web'
        web_dir.mkdir(parents=True, exist_ok=True)

        def normalize(u: str) -> str:
            u, _ = urldefrag(u)
            parsed = urlparse(u)
            normalized = parsed._replace(fragment='').geturl()
            return normalized

        def safe_filename_from_url(u: str, idx: int) -> str:
            parsed = urlparse(u)
            path = parsed.path or '/'
            slug = f"{parsed.netloc}{path}"
            slug = re.sub(r"[^A-Za-z0-9]+", "_", slug).strip("_")
            if not slug:
                slug = "root"
            slug = slug[:120]
            return f"scraped_{slug}_{idx}.txt"
        
        while to_visit and scraped_count < max_pages:
            url = to_visit.pop(0)
            url = normalize(url)

            if url in visited:
                continue

            visited.add(url)
            
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                
                text = self.html_converter.handle(str(soup))
                
                filename = safe_filename_from_url(url, scraped_count)
                output_path = web_dir / filename
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Scraped from: {url}\n\n")
                    f.write(text)
                
                logger.info(f"Scraped {url} -> {filename}")
                scraped_count += 1
                
                for link in soup.find_all('a', href=True):
                    full_url = urljoin(url, link['href'])
                    full_url = normalize(full_url)
                    parsed_full = urlparse(full_url)
                    full_path = parsed_full.path if parsed_full.path else '/'
                    if not full_path.endswith('/'):
                        full_path_check = full_path + '/'
                    else:
                        full_path_check = full_path

                    if (parsed_full.netloc == base_domain and
                        full_path_check.startswith(base_path) and
                        full_url not in visited and
                        full_url not in to_visit):
                        to_visit.append(full_url)
                
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
        
        logger.info(f"Scraping complete. Scraped {scraped_count} pages.")


if __name__ == "__main__":
    scraper = WebScraper()
    
    urls = [
        # "https://www.cmhc-schl.gc.ca/consumers/owning-a-home/mortgage-management/mortgage-fraud",
        # "https://www.cmhc-schl.gc.ca/professionals",
        # "https://www.canada.ca/en/financial-consumer-agency/services/mortgages.html",
        # "https://www.ratehub.ca/mortgages",
        # "https://www.bankofcanada.ca",
        # "https://www.ratehub.ca/prime-rate",
        # "https://www.ratehub.ca/best-mortgage-rates"
        "https://www.canada.ca/en/financial-consumer-agency/services/buying-home.html"
    ]
    
    for url in urls:
        scraper.scrape_mortgage_site(url, max_pages=15)
