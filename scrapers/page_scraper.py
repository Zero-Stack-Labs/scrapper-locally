"""Page scraper for product listing pages."""

import json
from typing import List, Optional
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from models.product import Product


class PageScraper(BaseScraper):
    """Scraper for product listing pages."""
    
    def get_products_page(self, page: int) -> Optional[str]:
        """
        Get a page of products from the listing.
        
        Args:
            page: Page number to scrape
            
        Returns:
            HTML content or None if failed
        """
        url = f"https://www.locally.com/search/all/activities/depts?store={self.store_id}&sort=pop&page={page}"
        
        response = self.make_request(url)
        
        if response is None:
            return None
        
        if response.status_code == 200:
            return response.text
        elif response.status_code == 404:
            print(f"Page {page} not found (404) - No more pages")
            return None
        else:
            print(f"Error {response.status_code} on page {page}")
            return None
    
    def extract_products_from_html(self, html: str) -> List[Product]:
        """
        Extract product information from JSON-LD in HTML.
        
        Args:
            html: HTML content of the page
            
        Returns:
            List of Product objects
        """
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        
        # Find the JSON-LD scripts
        json_scripts = soup.find_all('script', type='application/ld+json')
        
        for script in json_scripts:
            try:
                json_data = json.loads(script.string)
                
                # If it's a list of products
                if isinstance(json_data, list):
                    for item in json_data:
                        if item.get('@type') == 'Product':
                            product = Product.from_json_ld(item)
                            if product:
                                products.append(product)
                
                # If it's a single product
                elif isinstance(json_data, dict) and json_data.get('@type') == 'Product':
                    product = Product.from_json_ld(json_data)
                    if product:
                        products.append(product)
                        
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON-LD: {e}")
                continue
        
        return products
    
    def scrape_page(self, page: int) -> List[Product]:
        """
        Scrape a single page and return products.
        
        Args:
            page: Page number to scrape
            
        Returns:
            List of Product objects found on the page
        """
        print(f"Scraping page {page}...")
        
        html = self.get_products_page(page)
        if not html:
            print(f"Could not get page {page}")
            return []
        
        products = self.extract_products_from_html(html)
        print(f"Found {len(products)} products on page {page}")
        
        # Set page number for each product
        for product in products:
            product.page_number = page
        
        return products
    
    def scrape_pages_range(self, start_page: int = 1, end_page: Optional[int] = None) -> List[Product]:
        """
        Scrape a range of pages.
        
        Args:
            start_page: Starting page number
            end_page: Ending page number (None for all pages until empty)
            
        Returns:
            List of all Product objects found
        """
        all_products = []
        page = start_page
        
        while True:
            if end_page is not None and page > end_page:
                break
            
            products = self.scrape_page(page)
            
            if not products:
                print(f"No products found on page {page}. Stopping.")
                break
            
            all_products.extend(products)
            page += 1
        
        return all_products 