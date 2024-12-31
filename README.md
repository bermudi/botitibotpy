# Social Media Content Creation Framework

This framework provides a Python-based solution for generating and managing social media content across multiple platforms using LLMs. It leverages LlamaIndex for content generation, supports web page parsing and RSS feed reading for content ideas, and integrates with the Bluesky and Twitter APIs.

## Features

- **Multi-Platform Support:** Supports content creation and management on Instagram, Twitter, Bluesky, and potentially other platforms.
- **LLM-Powered Content Generation:** Utilizes LlamaIndex for generating creative and engaging content.
- **Web Page Parsing:** Extracts relevant information from web pages to generate content ideas.
- **RSS Feed Reading:** Monitors RSS feeds for new content and trends to inspire content creation.
- **Comment Handling:** Automatically responds to comments on uploaded content.
- **Bluesky Integration:** Uses the `atproto.blue` library for interacting with the Bluesky API.
- **Twitter Integration:** Uses the `twitter-openapi-python` library for interacting with the Twitter API.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/social-media-framework.git
cd social-media-framework
```

2. Install the dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your environment variables:
```bash
export OPENAI_API_KEY="your_openai_key"
export TWITTER_API_KEY="your_twitter_api_key"
export TWITTER_API_SECRET="your_twitter_api_secret"
export TWITTER_ACCESS_TOKEN="your_twitter_access_token"
export TWITTER_ACCESS_SECRET="your_twitter_access_secret"
export BLUESKY_IDENTIFIER="your_bluesky_handle"
export BLUESKY_PASSWORD="your_bluesky_password"
```

## Usage

### Content Generation
```bash
python -m src.cli.cli generate "Write a tweet about AI in social media"
```

### Web Page Parsing
```bash
python -m src.cli.cli parse_webpage "https://www.example.com"
```

### RSS Feed Reading
```bash
python -m src.cli.cli read_rss "https://www.example.com/feed"
```

### Bluesky Integration
```bash
# Authenticate
python -m src.cli.cli bluesky auth your_handle your_password

# Create post
python -m src.cli.cli bluesky post "This is a test post on Bluesky"

# Get comments
python -m src.cli.cli bluesky comments "post_uri"

# Respond to comment
python -m src.cli.cli bluesky respond "comment_uri" "This is a response"
```

### Twitter Integration
```bash
# Authenticate
python -m src.cli.cli twitter auth api_key api_secret access_token access_secret

# Create tweet
python -m src.cli.cli twitter tweet "This is a test tweet"

# Get comments
python -m src.cli.cli twitter tweet_comments "tweet_id"

# Respond to comment
python -m src.cli.cli twitter tweet_respond "comment_id" "This is a response"
```

## Architecture

The framework is designed with a modular architecture, consisting of the following components:

1. **Content Generation Module:**
   - Uses LlamaIndex to generate content based on user prompts, parsed web pages, and RSS feed data.
   - Provides options for customizing content length, tone, and style.

2. **Social Media Integration Module:**
   - Handles authentication and API interactions for each supported social media platform.
   - Provides methods for uploading content, retrieving comments, and responding to comments.
   - Uses `atproto.blue` for Bluesky and `twitter-openapi-python` for Twitter.

3. **Data Handling Module:**
   - Parses web pages using libraries like `BeautifulSoup4`.
   - Reads and processes RSS feeds using libraries like `feedparser`.
   - Stores and manages content, comments, and other relevant data.

4. **Command-Line Interface (CLI):**
   - Provides a user-friendly interface for interacting with the framework.
   - Allows users to generate content, upload it to social media platforms, and manage comments.

## Dependencies

- Python 3.8+
- LlamaIndex
- `atproto.blue`
- `twitter-openapi-python`
- `feedparser`
- `requests`
- `BeautifulSoup4`
- `python-dotenv`

## Future Enhancements

- Support for more social media platforms
- Advanced content customization options
- Integration with other LLMs
- Improved comment handling and sentiment analysis
- Scheduling content posting
- Analytics and reporting

## Contributing

Contributions are welcome! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) file for details on how to get started.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
