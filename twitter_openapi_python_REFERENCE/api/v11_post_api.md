# V11PostApiUtils

This class provides utility functions for the v1.1 POST API endpoints.

## Methods

### `__init__(self, api: twitter.V11PostApi, flag: ParamType)`

Initializes the utility with an API client and a flag.

- `api`: An instance of `twitter.V11PostApi`.
- `flag`: A dictionary containing flag values.

### `request(self, apiFn: ApiFnType[T], key: str, param: ParamType) -> TwitterApiUtilsResponse[T]`

A generic request method that calls an API function and builds a `TwitterApiUtilsResponse`.

- `apiFn`: The API function to call.
- `key`: The key to use for the flag.
- `param`: Additional parameters for the API call.

### `post_create_friendships(self, user_id: str, extra_param: Optional[ParamType] = None) -> TwitterApiUtilsResponse[None]`

Creates a friendship (follows a user).

- `user_id`: The ID of the user to follow.
- `extra_param`: Additional parameters for the API call.

### `post_destroy_friendships(self, user_id: str, extra_param: Optional[ParamType] = None) -> TwitterApiUtilsResponse[None]`

Destroys a friendship (unfollows a user).

- `user_id`: The ID of the user to unfollow.
- `extra_param`: Additional parameters for the API call.
