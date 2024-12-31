import requests
import feedparser
from bs4 import BeautifulSoup
from typing import List, Dict
import re

class DataHandler:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }

    def clean_text(self, text: str) -> str:
        """
        Cleans and formats extracted text content.

        Args:
            text: The text to clean.

        Returns:
            The cleaned text.
        """
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove special characters except basic punctuation
        text = re.sub(r'[^\w\s.,!?]', '', text)
        return text

    def parse_webpage(self, url: str) -> str:
        """
        Parses a web page and extracts relevant text content.

        Args:
            url: The URL of the web page to parse.

        Returns:
            The extracted text content.
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'iframe']):
                element.decompose()
            
            # Extract and clean text
            text = soup.get_text()
            return self.clean_text(text)
        except Exception as e:
            return f"Error parsing webpage: {str(e)}"

    def read_rss_feed(self, url: str) -> List[Dict[str, str]]:
        """
        Reads an RSS feed and extracts the latest entries.

        Args:
            url: The URL of the RSS feed.

        Returns:
            A list of dictionaries containing entry details.
        """
        try:
            feed = feedparser.parse(url)
            entries = []
            
            for entry in feed.entries:
                entry_data = {
                    'title': entry.get('title', ''),
                    'summary': self.clean_text(entry.get('summary', '')),
                    'link': entry.get('link', ''),
                    'published': entry.get('published', '')
                }
                entries.append(entry_data)
            
            return entries
        except Exception as e:
            return [{'error': f"Error reading RSS feed: {str(e)}"}]

def parse_webpage(url: str) -> str:
    """
    Convenience function for parsing web pages using default settings.

    Args:
        url: The URL of the web page to parse.

    Returns:
        The extracted text content.
    """
    handler = DataHandler()
    return handler.parse_webpage(url)

def read_rss_feed(url: str) -> List[Dict[str, str]]:
    """
    Convenience function for reading RSS feeds using default settings.

    Args:
        url: The URL of the RSS feed.

    Returns:
        A list of dictionaries containing entry details.
    """
    handler = DataHandler()
    return handler.read_rss_feed(url)

if __name__ == '__main__':
    # Test with a real webpage
    test_webpage_url = "https://www.example.com"
    parsed_webpage_content = parse_webpage(test_webpage_url)
    print(f"Parsed webpage content: {parsed_webpage_content}")

    # Test with a real RSS feed
    test_rss_feed_url = "https://www.example.com/rss"
    rss_feed_entries = read_rss_feed(test_rss_feed_url)
    print(f"RSS feed entries: {rss_feed_entries}")
