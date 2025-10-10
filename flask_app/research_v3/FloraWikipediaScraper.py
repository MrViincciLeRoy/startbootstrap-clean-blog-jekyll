
import requests
from bs4 import BeautifulSoup
import sqlite3
from typing import Dict, Optional
import time

class FloraWikipediaScraper:
    def __init__(self, db_name: str = "flora_data.db"):
        """Initialize the scraper with database connection."""
        self.db_name = db_name
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.setup_database()

    def setup_database(self):
        """Create the database schema."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS flora_plants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                title TEXT,
                scientific_name TEXT,
                kingdom TEXT,
                clade TEXT,
                order_name TEXT,
                family TEXT,
                subfamily TEXT,
                tribe TEXT,
                subtribe TEXT,
                genus TEXT,
                species TEXT,
                image_url TEXT,
                image_caption TEXT,
                complete BOOLEAN DEFAULT 0,
                raw_data TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()
        print(f"Database '{self.db_name}' initialized successfully.")

    def fetch_flora_category_links(self, category_url: str) -> list:
        """
        Fetch all plant links from Wikipedia Flora category page.

        Args:
            category_url: URL of the Wikipedia category page

        Returns:
            List of URLs to individual plant pages
        """
        print(f"Fetching links from: {category_url}")

        response = requests.get(category_url, headers=self.headers)
        if response.status_code != 200:
            print(f"Failed to retrieve the page. Status code: {response.status_code}")
            return []

        soup = BeautifulSoup(response.content, 'html.parser')
        div_mw_pages = soup.find('div', id='mw-pages')

        if not div_mw_pages:
            print("Div with ID 'mw-pages' not found.")
            return []

        # Extract all links inside mw-pages
        all_links = [link.get('href') for link in div_mw_pages.find_all('a', href=True)]

        # Slice from the 4th link onward (index 3) and exclude the last one
        if len(all_links) < 4:
            print("Not enough links to slice.")
            return []

        filtered_links = all_links[3:-1]

        # Convert to absolute URLs
        absolute_urls = [f"https://en.wikipedia.org{link}" for link in filtered_links]

        print(f"Found {len(absolute_urls)} plant pages.")
        return absolute_urls

    def scrape_wikipedia_infobox(self, url: str) -> Optional[Dict[str, str]]:
        """
        Scrape the infobox from a Wikipedia page.

        Args:
            url: Wikipedia page URL

        Returns:
            Dictionary with infobox data or None if not found
        """
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find the infobox
            infobox = soup.find('table', {'class': lambda x: x and 'infobox' in x})

            if not infobox:
                return None

            infobox_data = {}
            rows = infobox.find_all('tr')

            for row in rows:
                headers = row.find_all('th')
                cells = row.find_all('td')

                # Case 1: Row has both th and td (label: value)
                if len(headers) == 1 and len(cells) == 1:
                    key = headers[0].get_text(strip=True).rstrip(':')
                    value = cells[0].get_text(separator=' ', strip=True)
                    if key:
                        infobox_data[key] = value

                # Case 2: Row has only th spanning full width
                elif len(headers) == 1 and len(cells) == 0:
                    colspan = headers[0].get('colspan')
                    if colspan:
                        text = headers[0].get_text(strip=True)
                        if text and 'title' not in infobox_data:
                            infobox_data['title'] = text

                # Case 3: Row has two td elements
                elif len(cells) == 2 and len(headers) == 0:
                    key = cells[0].get_text(strip=True).rstrip(':')
                    value = cells[1].get_text(separator=' ', strip=True)
                    if key and value:
                        infobox_data[key] = value

                # Case 4: Row has only one td
                elif len(cells) == 1 and len(headers) == 0:
                    cell = cells[0]

                    # Check for image
                    img = cell.find('img')
                    if img:
                        img_src = img.get('src', '')
                        if img_src and 'image' not in infobox_data:
                            infobox_data['image'] = 'https:' + img_src if img_src.startswith('//') else img_src

                    # Check for caption
                    text = cell.get_text(strip=True)
                    if text and 'image' in infobox_data and 'image_caption' not in infobox_data:
                        if len(text) < 200 and not text.startswith('Scientific classification'):
                            infobox_data['image_caption'] = text

            return infobox_data

        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None

    def extract_scientific_name(self, infobox_data: Dict[str, str]) -> Optional[str]:
        """Extract scientific name from infobox data."""
        # Common keys that might contain scientific name
        possible_keys = ['Binomial name', 'Scientific name', 'Genus', 'Species']

        for key in possible_keys:
            if key in infobox_data:
                return infobox_data[key]

        return None

    def save_to_database(self, url: str, infobox_data: Optional[Dict[str, str]]):
        """Save scraped data to database."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        if infobox_data:
            scientific_name = self.extract_scientific_name(infobox_data)

            cursor.execute('''
                INSERT OR REPLACE INTO flora_plants (
                    url, title, scientific_name, kingdom, clade, order_name,
                    family, subfamily, tribe, subtribe, genus, species,
                    image_url, image_caption, complete, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                url,
                infobox_data.get('title'),
                scientific_name,
                infobox_data.get('Kingdom'),
                infobox_data.get('Clade'),
                infobox_data.get('Order'),
                infobox_data.get('Family'),
                infobox_data.get('Subfamily'),
                infobox_data.get('Tribe'),
                infobox_data.get('Subtribe'),
                infobox_data.get('Genus'),
                infobox_data.get('Species'),
                infobox_data.get('image'),
                infobox_data.get('image_caption'),
                1,  # complete = True
                str(infobox_data)  # Store raw data as JSON string
            ))
        else:
            # Insert URL with complete = False if scraping failed
            cursor.execute('''
                INSERT OR IGNORE INTO flora_plants (url, complete)
                VALUES (?, 0)
            ''', (url,))

        conn.commit()
        conn.close()

    def scrape_all_flora_pages(self, category_url: str, delay: float = 1.0):
        """
        Main method to scrape all flora pages from category.

        Args:
            category_url: Wikipedia category URL
            delay: Delay between requests in seconds (be polite!)
        """
        # Step 1: Get all plant page URLs
        plant_urls = self.fetch_flora_category_links(category_url)

        if not plant_urls:
            print("No plant URLs found.")
            return

        # Step 2: Scrape each plant page
        total = len(plant_urls)
        print(f"\nStarting to scrape {total} plant pages...\n")

        for i, url in enumerate(plant_urls, 1):
            print(f"[{i}/{total}] Scraping: {url}")

            # Scrape infobox data
            infobox_data = self.scrape_wikipedia_infobox(url)

            # Save to database
            self.save_to_database(url, infobox_data)

            if infobox_data:
                print(f"  ✓ Successfully scraped: {infobox_data.get('title', 'Unknown')}")
            else:
                print(f"  ✗ No infobox found")

            # Be polite - add delay between requests
            if i < total:
                time.sleep(delay)

        print(f"\n{'='*60}")
        print(f"Scraping complete! Data saved to '{self.db_name}'")
        print(f"{'='*60}")

    def get_statistics(self):
        """Print database statistics."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM flora_plants")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM flora_plants WHERE complete = 1")
        complete = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM flora_plants WHERE complete = 0")
        incomplete = cursor.fetchone()[0]

        conn.close()

        print(f"\nDatabase Statistics:")
        print(f"  Total entries: {total}")
        print(f"  Complete: {complete}")
        print(f"  Incomplete: {incomplete}")


# Example usage
if __name__ == "__main__":
    # Initialize scraper
    scraper = FloraWikipediaScraper(db_name="flora_data.db")

    # Category URL
    category_url = "https://en.wikipedia.org/wiki/Category:Flora_of_Southern_Africa"

    # Start scraping (with 1 second delay between requests)
    scraper.scrape_all_flora_pages(category_url, delay=1.0)

    # Show statistics
    scraper.get_statistics()