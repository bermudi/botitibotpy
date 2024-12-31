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

Use of environment variables/.env file:
```bash
export OPENAI_API_KEY="your_openai_key"
export TWITTER_API_KEY="your_twitter_api_key"
export TWITTER_API_SECRET="your_twitter_api_secret"
export TWITTER_ACCESS_TOKEN="your_twitter_access_token"
export TWITTER_ACCESS_SECRET="your_twitter_access_secret"
export BLUESKY_IDENTIFIER="your_bluesky_handle"
export BLUESKY_PASSWORD="your_bluesky_password"
```

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