# V11GetApiUtils

This class provides utility functions for the v1.1 GET API endpoints.

## Methods

### `__init__(self, api: twitter.V11GetApi, flag: ParamType)`

Initializes the utility with an API client and a flag.

- `api`: An instance of `twitter.V11GetApi`.
- `flag`: A dictionary containing flag values.

### `request(self, apiFn: ApiFnType[T], key: str, param: ParamType) -> TwitterApiUtilsResponse[T]`

A generic request method that calls an API function and builds a `TwitterApiUtilsResponse`.

- `apiFn`: The API function to call.
- `key`: The key to use for the flag.
- `param`: Additional parameters for the API call.

### `get_friends_following_list(self, user_id: str, cursor: Optional[str] = None, count: Optional[int] = None, extra_param: Optional[ParamType] = None) -> TwitterApiUtilsResponse[None]`

Retrieves a list of users that a user is following.

- `user_id`: The ID of the user.
- `cursor`: The cursor for pagination.
- `count`: The number of items to retrieve.
- `extra_param`: Additional parameters for the API call.

### `get_search_typeahead(self, q: str, extra_param: Optional[ParamType] = None) -> TwitterApiUtilsResponse[None]`

Retrieves search typeahead suggestions.

- `q`: The search query.
- `extra_param`: Additional parameters for the API call.
