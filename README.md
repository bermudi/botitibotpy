# Social Media Content Creation Bot

This Bot provides a Python-based solution for generating and managing social media content across multiple platforms using LLMs. It leverages LlamaIndex for content generation, supports web page parsing and RSS feed reading for content ideas, and integrates with the Bluesky and Twitter APIs.

## Features

- **Multi-Platform Support:** Currently supports content creation and management on Twitter and Bluesky.
- **LLM-Powered Content Generation:** Utilizes LlamaIndex and OpenAI for generating creative and engaging content, with Gemini for embeddings.
- **Content Source Integration:** Parses web pages and monitors RSS feeds for content inspiration.
- **Automated Scheduling:** Handles content generation, posting, and engagement monitoring on configurable intervals.
- **Comment Handling:** Automatically responds to comments on posted content.

## Key Functionalities

*   **User Authentication:** 
    - Twitter: Cookie-based authentication with retry mechanisms
    - Bluesky: Standard API authentication
*   **Data Persistence:** SQLite database with comprehensive schema for credentials, posts, comments, and metrics
*   **Content Generation:** 
    - LlamaIndex with ChromaDB for vector storage
    - Content customization (length, tone, style)
    - Web page parsing and RSS feed monitoring
*   **Social Media Integration:**
    - Full Twitter API support via `twitter-openapi-python`
    - Complete Bluesky integration via `atproto`
    - Timeline and feed fetching
    - Engagement tracking
    - Automated responses
*   **Social Media Posting:** The bot can create posts on Bluesky, Instagram and Twitter.
*   **Timeline Fetching:** The bot can fetch timelines from Bluesky, Instagram and Twitter.
*   **Author Feed Fetching:** The bot can fetch the author's feed from Bluesky, Instagram and Twitter.
*   **Comment Management:** The bot can create and fetch comments on Bluesky, Instagram and Twitter.
*   **Social Media Interaction:** The bot automatically checks for comments on uploaded content and replies to it when running
*   **Real-time Communication:** The bot server backend uses WebSockets for real-time communication with the client application.
*   **Error Handling:** Comprehensive logging and retry mechanisms
*   **Bluesky Integration:** Uses the `atproto.blue` library for interacting with the Bluesky API.
*   **Twitter Integration:** Uses the `twitter-openapi-python` library for interacting with the Twitter API.

## Architecture

The Bot is designed with a modular architecture:

1. **Content Generation Module:**
   - LlamaIndex + ChromaDB for content storage and retrieval
   - OpenAI for content generation
   - Gemini for embeddings
   - Web page parsing and RSS feed monitoring
   - Content customization options

2. **Social Media Module:**
   - Platform-specific clients (Twitter, Bluesky)
   - Authentication management
   - API interaction handling
   - Engagement tracking

3. **Scheduler Module:** 
   - Async task management
   - Configurable intervals
   - Task monitoring and metrics collection

4. **Database Module:**
   - SQLite with SQLAlchemy ORM
   - Comprehensive schema design
   - Migration system

5. **CLI Interface (Coming Soon):**
   - Content management
   - System monitoring
   - Task control
   - Testing utilities

6. **API Interface (Planned):**
   - RESTful endpoints
   - WebSocket support
   - Authentication/authorization
   - Comprehensive documentation

## Dependencies

- Python 3.9+
- LlamaIndex + ChromaDB
- OpenAI API
- Gemini API
- `atproto`
- `twitter-openapi-python`
- `beautifulsoup4`
- `feedparser`
- `sqlalchemy`

## Setup

```shell
pip install -r requirements.txt
```

Configure your environment variables:
```shell
# LLM APIs
OPENAI_API_KEY=your_key
GOOGLE_API_KEY=your_key

# Twitter
TWITTER_USERNAME=your_username
TWITTER_PASSWORD=your_password

# Bluesky
BLUESKY_IDENTIFIER=your_identifier
BLUESKY_PASSWORD=your_password
```

