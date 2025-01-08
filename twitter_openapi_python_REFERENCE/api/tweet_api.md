# TweetApiUtils

This class provides utility functions for the tweet API endpoints.

## Methods

### `__init__(self, api: twitter.TweetApi, flag: ParamType)`

Initializes the utility with an API client and a flag.

- `api`: An instance of `twitter.TweetApi`.
- `flag`: A dictionary containing flag values.

### `request(self, apiFn: ApiFnType[T], convertFn: Callable[[T], List[models.InstructionUnion]], key: str, param: ParamType) -> ResponseType`

A generic request method that calls an API function, converts the response, and builds a `TwitterApiUtilsResponse`.

- `apiFn`: The API function to call.
- `convertFn`: A function to convert the response data.
- `key`: The key to use for the flag.
- `param`: Additional parameters for the API call.

### `get_tweet_detail(self, focal_tweet_id: str, cursor: Optional[str] = None, controller_data: Optional[str] = None, extra_param: Optional[ParamType] = None) -> ResponseType`

Retrieves details of a tweet.

- `focal_tweet_id`: The ID of the tweet.
- `cursor`: The cursor for pagination.
- `controller_data`: Additional controller data.
- `extra_param`: Additional parameters for the API call.

### `get_search_timeline(self, raw_query: str, product: Optional[str] = None, cursor: Optional[str] = None, count: Optional[int] = None, extra_param: Optional[ParamType] = None) -> ResponseType`

Retrieves a search timeline.

- `raw_query`: The search query.
- `product`: The product type.
- `cursor`: The cursor for pagination.
- `count`: The number of items to retrieve.
- `extra_param`: Additional parameters for the API call.

### `get_home_timeline(self, cursor: Optional[str] = None, count: Optional[int] = None, extra_param: Optional[ParamType] = None) -> ResponseType`

Retrieves the home timeline.

- `cursor`: The cursor for pagination.
- `count`: The number of items to retrieve.
- `extra_param`: Additional parameters for the API call.

### `get_home_latest_timeline(self, cursor: Optional[str] = None, count: Optional[int] = None, extra_param: Optional[ParamType] = None) -> ResponseType`

Retrieves the latest home timeline.

- `cursor`: The cursor for pagination.
- `count`: The number of items to retrieve.
- `extra_param`: Additional parameters for the API call.

### `get_list_latest_tweets_timeline(self, list_id: str, cursor: Optional[str] = None, count: Optional[int] = None, extra_param: Optional[ParamType] = None) -> ResponseType`

Retrieves the latest tweets from a list.

- `list_id`: The ID of the list.
- `cursor`: The cursor for pagination.
- `count`: The number of items to retrieve.
- `extra_param`: Additional parameters for the API call.

### `get_user_tweets(self, user_id: str, cursor: Optional[str] = None, count: Optional[int] = None, extra_param: Optional[ParamType] = None) -> ResponseType`

Retrieves tweets from a user.

- `user_id`: The ID of the user.
- `cursor`: The cursor for pagination.
- `count`: The number of items to retrieve.
- `extra_param`: Additional parameters for the API call.

### `get_user_tweets_and_replies(self, user_id: str, cursor: Optional[str] = None, count: Optional[int] = None, extra_param: Optional[ParamType] = None) -> ResponseType`

Retrieves tweets and replies from a user.

- `user_id`: The ID of the user.
- `cursor`: The cursor for pagination.
- `count`: The number of items to retrieve.
- `extra_param`: Additional parameters for the API call.

### `get_user_media(self, user_id: str, cursor: Optional[str] = None, count: Optional[int] = None, extra_param: Optional[ParamType] = None) -> ResponseType`

Retrieves media from a user.

- `user_id`: The ID of the user.
- `cursor`: The cursor for pagination.
- `count`: The number of items to retrieve.
- `extra_param`: Additional parameters for the API call.

### `get_likes(self, user_id: str, cursor: Optional[str] = None, count: Optional[int] = None, extra_param: Optional[ParamType] = None) -> ResponseType`

Retrieves likes from a user.

- `user_id`: The ID of the user.
- `cursor`: The cursor for pagination.
- `count`: The number of items to retrieve.
- `extra_param`: Additional parameters for the API call.

### `get_bookmarks(self, cursor: Optional[str] = None, count: Optional[int] = None, extra_param: Optional[ParamType] = None) -> ResponseType`

Retrieves bookmarks.

- `cursor`: The cursor for pagination.
- `count`: The number of items to retrieve.
- `extra_param`: Additional parameters for the API call.
