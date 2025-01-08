# UserListApiUtils

This class provides utility functions for the user list API endpoints.

## Methods

### `__init__(self, api: twitter.UserListApi, flag: ParamType)`

Initializes the utility with an API client and a flag.

- `api`: An instance of `twitter.UserListApi`.
- `flag`: A dictionary containing flag values.

### `request(self, apiFn: ApiFnType[T], convertFn: Callable[[T], List[models.InstructionUnion]], key: str, param: ParamType) -> ResponseType`

A generic request method that calls an API function, converts the response, and builds a `TwitterApiUtilsResponse`.

- `apiFn`: The API function to call.
- `convertFn`: A function to convert the response data.
- `key`: The key to use for the flag.
- `param`: Additional parameters for the API call.

### `get_followers(self, user_id: str, cursor: Optional[str] = None, count: Optional[int] = None, extra_param: Optional[ParamType] = None) -> ResponseType`

Retrieves followers of a user.

- `user_id`: The ID of the user.
- `cursor`: The cursor for pagination.
- `count`: The number of items to retrieve.
- `extra_param`: Additional parameters for the API call.

### `get_following(self, user_id: str, cursor: Optional[str] = None, count: Optional[int] = None, extra_param: Optional[ParamType] = None) -> ResponseType`

Retrieves users that a user is following.

- `user_id`: The ID of the user.
- `cursor`: The cursor for pagination.
- `count`: The number of items to retrieve.
- `extra_param`: Additional parameters for the API call.

### `get_followers_you_know(self, user_id: str, cursor: Optional[str] = None, count: Optional[int] = None, extra_param: Optional[ParamType] = None) -> ResponseType`

Retrieves followers that a user knows.

- `user_id`: The ID of the user.
- `cursor`: The cursor for pagination.
- `count`: The number of items to retrieve.
- `extra_param`: Additional parameters for the API call.

### `get_favoriters(self, tweet_id: str, cursor: Optional[str] = None, count: Optional[int] = None, extra_param: Optional[ParamType] = None) -> ResponseType`

Retrieves users who favorited a tweet.

- `tweet_id`: The ID of the tweet.
- `cursor`: The cursor for pagination.
- `count`: The number of items to retrieve.
- `extra_param`: Additional parameters for the API call.

### `get_retweeters(self, tweet_id: str, cursor: Optional[str] = None, count: Optional[int] = None, extra_param: Optional[ParamType] = None) -> ResponseType`

Retrieves users who retweeted a tweet.

- `tweet_id`: The ID of the tweet.
- `cursor`: The cursor for pagination.
- `count`: The number of items to retrieve.
- `extra_param`: Additional parameters for the API call.
