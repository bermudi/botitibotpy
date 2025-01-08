# UserApiUtils

This class provides utility functions for the user API endpoints.

## Methods

### `__init__(self, api: twitter.UserApi, flag: ParamType)`

Initializes the utility with an API client and a flag.

- `api`: An instance of `twitter.UserApi`.
- `flag`: A dictionary containing flag values.

### `request(self, apiFn: ApiFnType[T], convertFn: Callable[[T], models.UserResults], key: str, param: ParamType) -> ResponseType`

A generic request method that calls an API function, converts the response, and builds a `TwitterApiUtilsResponse`.

- `apiFn`: The API function to call.
- `convertFn`: A function to convert the response data.
- `key`: The key to use for the flag.
- `param`: Additional parameters for the API call.

### `get_user_by_screen_name(self, screen_name: str, extra_param: Optional[ParamType] = None) -> ResponseType`

Retrieves a user by their screen name.

- `screen_name`: The screen name of the user.
- `extra_param`: Additional parameters for the API call.

### `get_user_by_rest_id(self, user_id: str, extra_param: Optional[ParamType] = None) -> ResponseType`

Retrieves a user by their REST ID.

- `user_id`: The ID of the user.
- `extra_param`: Additional parameters for the API call.
