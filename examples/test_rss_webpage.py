import logging
from src.content.generator import ContentGenerator

def main():
    # Initialize the content generator with debug logging
    generator = ContentGenerator(log_level=logging.DEBUG)
    
    # Test RSS feed functions
    
    # Sample RSS feed URLs
    rss_feeds = [
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        "https://feeds.bbci.co.uk/news/technology/rss.xml"
    ]
    
    # Test parse_rss_feed
    print("\nTesting parse_rss_feed:")
    for feed_url in rss_feeds:
        print(f"\nParsing feed: {feed_url}")
        documents = generator.parse_rss_feed(feed_url)
        if documents:
            print(f"Found {len(documents)} entries")
            for doc in documents[:2]:  # Show first 2 entries
                print(f"Title: {doc.metadata['title']}")
                print(f"Published: {doc.metadata.get('published_date', 'unknown')}")
                print(f"Content preview: {doc.text[:100]}...")
        else:
            print("Failed to parse feed")
    
    # Test monitor_rss_feed
    print("\nTesting monitor_rss_feed:")
    for feed_url in rss_feeds:
        print(f"\nMonitoring feed: {feed_url}")
        new, failed = generator.monitor_rss_feed(feed_url)
        print(f"New entries: {new}, Failed entries: {failed}")
    
    # Test webpage functions
    
    # Sample webpage URLs
    webpages = [
        "https://www.example.com",
        "https://www.wikipedia.org"
    ]
    
    # Test load_webpage
    print("\nTesting load_webpage:")
    for url in webpages:
        print(f"\nLoading webpage: {url}")
        doc = generator.load_webpage(url)
        if doc:
            print(f"Title: {doc.metadata['title']}")
            print(f"Content preview: {doc.text[:200]}...")
        else:
            print("Failed to load webpage")
    
    # Test load_webpage_batch
    print("\nTesting load_webpage_batch:")
    documents = generator.load_webpage_batch(webpages)
    print(f"Successfully loaded {len(documents)} webpages")
    
    # Test add_webpage_to_index
    print("\nTesting add_webpage_to_index:")
    for url in webpages:
        print(f"\nAdding webpage to index: {url}")
        success = generator.add_webpage_to_index(url)
        print(f"Success: {success}")

if __name__ == "__main__":
    main()
