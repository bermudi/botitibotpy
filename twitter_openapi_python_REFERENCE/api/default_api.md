# DefaultApiUtils

This class provides utility functions for the default API endpoints.

## Methods

### `__init__(self, api: twitter.DefaultApi, flag: ParamType)`

Initializes the utility with an API client and a flag.

- `api`: An instance of `twitter.DefaultApi`.
- `flag`: A dictionary containing flag values.

### `request(self, apiFn: ApiFnType[T1], convertFn: Callable[[T1], T2], key: str, param: ParamType)`

A generic request method that calls an API function, converts the response, and builds a `TwitterApiUtilsResponse`.

- `apiFn`: The API function to call.
- `convertFn`: A function to convert the response data.
- `key`: The key to use for the flag.
- `param`: Additional parameters for the API call.

### `get_profile_spotlights_query(self, screen_name: Optional[str] = None, extra_param: Optional[ParamType] = None) -> TwitterApiUtilsResponse[models.UserResultByScreenName]`

Retrieves profile spotlights for a given screen name.

- `screen_name`: The screen name of the user.
- `extra_param`: Additional parameters for the API call.

### `get_tweet_result_by_rest_id(self, tweet_id: str, extra_param: Optional[ParamType] = None) -> TwitterApiUtilsResponse[TweetApiUtilsData]`

Retrieves a tweet by its REST ID.

- `tweet_id`: The ID of the tweet.
- `extra_param`: Additional parameters for the API call.
