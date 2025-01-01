from src.social.bluesky import BlueskyClient

def test_bluesky_basic():
    # Initialize client
    client = BlueskyClient()
    
    # Test posting
    test_post = client.post_content("🤖 Hello! This is a test post from my Python bot!")
    if test_post:
        print("✅ Post successful!")
        print(f"Post URI: {test_post.uri}")
        
        # Test fetching the post thread
        thread = client.get_post_thread(test_post.uri)
        if thread:
            print("✅ Thread fetch successful!")
        
        # Test timeline fetch
        timeline = client.get_timeline(limit=5)
        if timeline:
            print("✅ Timeline fetch successful!")
            print("\nRecent posts in timeline:")
            for post in timeline.feed:
                try:
                    print(f"- {post.post.record.text[:50]}...")
                except Exception as e:
                    print(f"- [Error reading post: {e}]")

if __name__ == "__main__":
    test_bluesky_basic() 