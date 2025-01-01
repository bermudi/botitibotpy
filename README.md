# Social Media Content Creation Bot

This Bot provides a Python-based solution for generating and managing social media content across multiple platforms using LLMs. It leverages LlamaIndex for content generation, supports web page parsing and RSS feed reading for content ideas, and integrates with the Bluesky and Twitter APIs.

## Features

- **Multi-Platform Support:** Supports content creation and management on Instagram, Twitter, Bluesky, and potentially other platforms.
- **LLM-Powered Content Generation:** Utilizes LlamaIndex for generating creative and engaging content.
- **Comment Handling:** Automatically responds to comments on uploaded content.

## Key Functionalities

*   **User Authentication:** The server authenticates with social media platforms using credentials stored in the database.
*   **Data Persistence:** The server uses an SQLite database to store credentials, posts, comments and replies.
*   **Content Generation:** The server uses an Llama Index to generate content.
      - **Web Page Parsing:** Extracts relevant information from web pages to generate content ideas.
      - **RSS Feed Reading:** Monitors RSS feeds for new content and trends to inspire content creation.
*   **Social Media Posting:** The server can create posts on Bluesky, Instagram and Twitter.
*   **Timeline Fetching:** The server can fetch timelines from Bluesky, Instagram and Twitter.
*   **Author Feed Fetching:** The server can fetch the author's feed from Bluesky, Instagram and Twitter.
*   **Comment Management:** The server can create and fetch comments on Bluesky, Instagram and Twitter.
*   **Social Media Interaction:** The server automatically responds to comments on uploaded content
*   **Real-time Communication:** The server uses WebSockets for real-time communication with the client application.
*   **Error Handling:** The server includes error handling and logging for all operations.
*   **Bluesky Integration:** Uses the `atproto.blue` library for interacting with the Bluesky API.
*   **Twitter Integration:** Uses the `twitter-openapi-python` library for interacting with the Twitter API.

## Architecture

The Bot is designed with a modular architecture, consisting of the following components:

1. **Content Generation Module:**
   - Uses LlamaIndex to generate content based on user prompts, parsed web pages, and RSS feed data.
   - Provides options for customizing content length, tone, and style.
      - **Web Page Parsing:** Extracts relevant information from web pages to generate content ideas.
      - **RSS Feed Reading:** Monitors RSS feeds for new content and trends to inspire content creation.

2. **Scheduler:** 
   - Schedules content generation at configured intervals
   - Checks for replies every 5 minutes.
   - Updates engagement metrics for generated content every 10 minutes.

3. **Social Media Integration Module:**
   - Handles authentication and API interactions for each supported social media platform.
   - Provides methods for uploading content, retrieving comments, and responding to comments.
   - Uses `atproto.blue` for Bluesky and `twitter-openapi-python` for Twitter.

4. **Data Handling Module:**
   - Parses web pages using libraries like `BeautifulSoup4`.
   - Reads and processes RSS feeds using libraries like `feedparser`.
   - Stores and manages content, comments, and other relevant data.

5. **API Interface:**
   - Provides a REST API for interacting with the Bot.
   - Allows users to generate content, upload it to social media platforms, and manage comments.

## Dependencies

- Python 3.9+
- LlamaIndex
- `atproto.blue`
- `twitter-openapi-python`


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
```



## License

This project is dual licensed. You can choose one of the following licenses:

- [Custom License](./LICENSE)
- [GNU Affero General Public License v3.0](./LICENSE.AGPL)

## Development Plan

### Phase 1: Basic Infrastructure & Social Media Integration
- [x] Project structure setup
- [x] Configuration management
- [ ] Basic Bluesky integration
  - [x] Authentication
  - [x] Basic posting
  - [ ] Timeline fetching
  - [ ] Comment handling
- [ ] Basic Twitter integration
  - [x] Client setup
  - [ ] Authentication
  - [ ] Basic posting
  - [ ] Timeline fetching
  - [ ] Comment handling

### Phase 2: Content Generation
- [ ] LlamaIndex integration
  - [ ] Setup and configuration
  - [ ] Basic prompt handling
  - [ ] Content generation pipeline
- [ ] Content customization
  - [ ] Length control
  - [ ] Tone adjustment
  - [ ] Style parameters

### Phase 3: Content Source Integration
- [ ] Web Page Parser
  - [ ] HTML parsing setup
  - [ ] Content extraction
  - [ ] Metadata handling
- [ ] RSS Feed Reader
  - [ ] Feed parser setup
  - [ ] Content aggregation
  - [ ] Update monitoring

### Phase 4: Database & Persistence
- [ ] SQLite setup
  - [ ] Schema design
  - [ ] Migration system
- [ ] Model implementation
  - [ ] Credentials storage
  - [ ] Posts tracking
  - [ ] Comments/replies storage
  - [ ] Engagement metrics

### Phase 5: Scheduling & Automation
- [ ] Task Scheduler
  - [ ] Content generation scheduling
  - [ ] Posting schedule management
  - [ ] Reply checking automation
- [ ] Metrics Collection
  - [ ] Engagement tracking
  - [ ] Performance analytics
  - [ ] Report generation

### Phase 6: Testing & Refinement
- [ ] Test Suite Development
  - [ ] Unit tests
  - [ ] Integration tests
  - [ ] End-to-end tests
- [ ] Platform-specific testing
  - [ ] Bluesky test account setup
  - [ ] Twitter test account setup
  - [ ] Content generation testing
  - [ ] Interaction testing

### Phase 7: Advanced Features
- [ ] WebSocket Implementation
  - [ ] Real-time updates
  - [ ] Client communication
- [ ] Enhanced Error Handling
  - [ ] Logging system
  - [ ] Error recovery
  - [ ] Notification system
- [ ] Content Optimization
  - [ ] A/B testing
  - [ ] Performance analytics
  - [ ] Content refinement

## Current Status
- Completed basic project structure
- Implemented configuration management
- Started Bluesky integration
- Started Twitter integration

## Next Steps
1. Complete Bluesky integration with timeline fetching and comment handling
2. Finish Twitter authentication and basic posting
3. Begin LlamaIndex integration for content generation
4. Start implementing the web page parser

## Testing
Each phase includes its own testing milestones:
1. Create test accounts on both platforms
2. Implement unit tests for each component
3. Perform integration testing as components are connected
4. Conduct end-to-end testing for complete workflows

## Contributing
[Previous contributing section remains the same...]