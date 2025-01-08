# UsersApiUtils

This class provides utility functions for the users API endpoints.

## Methods

### `__init__(self, api: twitter.UsersApi, flag: ParamType)`

Initializes the utility with an API client and a flag.

- `api`: An instance of `twitter.UsersApi`.
- `flag`: A dictionary containing flag values.

### `request(self, apiFn: ApiFnType[T], convertFn: Callable[[T], list[models.UserResults]], key: str, param: ParamType) -> ResponseType`

A generic request method that calls an API function, converts the response, and builds a `TwitterApiUtilsResponse`.

- `apiFn`: The API function to call.
- `convertFn`: A function to convert the response data.
- `key`: The key to use for the flag.
- `param`: Additional parameters for the API call.

### `get_users_by_rest_ids(self, user_ids: list[str], extra_param: Optional[ParamType] = None) -> ResponseType`

Retrieves users by their REST IDs.

- `user_ids`: A list of user IDs.
- `extra_param`: Additional parameters for the API call.
