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
*   **Task Scheduling:**
    - Automated content generation (60-min intervals)
    - Reply checking (5-min intervals)
    - Metrics collection (10-min intervals)
*   **Error Handling:** Comprehensive logging and retry mechanisms

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

# twitter_openapi_python

## Setup

```shell
pip install twitter-openapi-python
```

## Usage

```python
import json
import datetime

from pathlib import Path
from tweepy_authlib import CookieSessionUserHandler
from twitter_openapi_python import TwitterOpenapiPython

# login by tweepy_authlib
if Path("cookie.json").exists():
    with open("cookie.json", "r") as f:
        cookies_dict = json.load(f)
        if isinstance(cookies_dict, list):
            cookies_dict = {k["name"]: k["value"] for k in cookies_dict}
else:
    auth_handler = CookieSessionUserHandler(
        screen_name=input("screen_name: "),
        password=input("password: "),
    )
    cookies_dict = auth_handler.get_cookies().get_dict()

# To extract cookies from Windows (Linux by default)
# If you use tweepy_authlib, you must be on Windows
client = TwitterOpenapiPython()
client.additional_api_headers = {
    "sec-ch-ua-platform": '"Windows"',
}
client.additional_browser_headers = {
    "sec-ch-ua-platform": '"Windows"',
}

# get client from cookies
client = client.get_client_from_cookies(cookies=cookies_dict)

# tweet "Hello World!!" with current time
time = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
client.get_post_api().post_create_tweet(tweet_text=f"Hello World!!{time}")

# get user info
response = client.get_user_api().get_user_by_screen_name("elonmusk")
```

### Login

```python
import json
from pathlib import Path

from requests.cookies import RequestsCookieJar
from tweepy_authlib import CookieSessionUserHandler


def login():
    if Path("cookie.json").exists():
        with open("cookie.json", "r") as f:
            cookies_dict = json.load(f)
        cookies = RequestsCookieJar()
        for key, value in cookies_dict.items():
            cookies.set(key, value)
        return CookieSessionUserHandler(cookies=cookies)
    else:
        auth_handler = CookieSessionUserHandler(
            screen_name=input("screen_name: "),
            password=input("password: "),
        )
        cookies = auth_handler.get_cookies()
        with open("cookie.json", "w") as f:
            json.dump(cookies.get_dict(), f, ensure_ascii=False, indent=4)
        return auth_handler
```

### User

```
import os
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import login as login
from twitter_openapi_python import TwitterOpenapiPython

cookies_dict = login.login().get_cookies().get_dict()
client = TwitterOpenapiPython().get_client_from_cookies(cookies=cookies_dict)
screen_name = "elonmusk"
user_response = client.get_user_api().get_user_by_screen_name(
    screen_name=screen_name,
)

print(f"rate_limit_remaining: {user_response.header.rate_limit_remaining}")
elonmusk = user_response.data.user
print(f"screen_name: {elonmusk.legacy.screen_name}")
print(f"friends_count: {elonmusk.legacy.friends_count}")
print(f"followers_count: {elonmusk.legacy.followers_count}")

os.makedirs("media", exist_ok=True)


url = urlparse(elonmusk.legacy.profile_image_url_https)
ext = os.path.splitext(url.path)[1]
data = urllib.request.urlopen(elonmusk.legacy.profile_image_url_https).read()
os.makedirs("media", exist_ok=True)
with open(Path("media", screen_name + ext), mode="wb+") as f:
    f.write(data)
```


### Tweet

```python
import datetime

import login as login
from twitter_openapi_python import TwitterOpenapiPython

cookies_dict = login.login().get_cookies().get_dict()
client = TwitterOpenapiPython().get_client_from_cookies(cookies=cookies_dict)

time = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
client.get_post_api().post_create_tweet(tweet_text=f"Hello World!!{time}")