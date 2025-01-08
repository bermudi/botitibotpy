# TwitterOpenapiPythonClient

This class is a client for the Twitter API. It provides methods to access different API endpoints.

## Methods

### `__init__(self, api: twitter.ApiClient, placeholder: ParamType)`

Initializes the client with an API client and a placeholder.

- `api`: An instance of `twitter.ApiClient`.
- `placeholder`: A dictionary containing placeholder values.

### `get_default_api(self) -> DefaultApiUtils`

Returns an instance of `DefaultApiUtils`.

### `get_initial_state_api(self) -> InitialStateApiUtils`

Returns an instance of `InitialStateApiUtils`.

### `get_post_api(self) -> PostApiUtils`

Returns an instance of `PostApiUtils`.

### `get_tweet_api(self) -> TweetApiUtils`

Returns an instance of `TweetApiUtils`.

### `get_user_api(self) -> UserApiUtils`

Returns an instance of `UserApiUtils`.

### `get_users_api(self) -> UsersApiUtils`

Returns an instance of `UsersApiUtils`.

### `get_user_list_api(self) -> UserListApiUtils`

Returns an instance of `UserListApiUtils`.

### `get_v11_get_api(self) -> V11GetApiUtils`

Returns an instance of `V11GetApiUtils`.

### `get_v11_post_api(self) -> V11PostApiUtils`

Returns an instance of `V11PostApiUtils`.

# TwitterOpenapiPython

This class provides methods to create and configure the Twitter API client.

## Attributes

- `hash`: A string representing the hash of the project.
- `placeholder_url`: A string representing the URL for the placeholder JSON file.
- `header`: A string representing the URL for the header JSON file.
- `access_token`: A string representing the access token.
- `twitter_url`: A string representing the Twitter URL.
- `additional_browser_headers`: A dictionary for additional browser headers.
- `additional_api_headers`: A dictionary for additional API headers.

## Methods

### `get_header(self) -> tuple[dict[str, str], dict[str, str]]`

Retrieves the header information from the header URL.

### `remove_prefix(self, text: str) -> str`

Removes the "x-twitter-" or "x-" prefix from a string.

### `kebab_to_upper_camel(self, text: dict[str, Any]) -> dict[str, Any]`

Converts keys from kebab-case to UpperCamelCase.

### `cookie_normalize(self, cookie: list[str]) -> dict[str, str]`

Normalizes a list of cookie strings into a dictionary.

### `cookie_to_str(self, cookie: dict[str, str]) -> str`

Converts a cookie dictionary to a string.

### `get_twitter_openapi_python_client(self, api: twitter.ApiClient) -> TwitterOpenapiPythonClient`

Creates a `TwitterOpenapiPythonClient` instance.

### `get_client_from_cookies(self, cookies: dict[str, str]) -> TwitterOpenapiPythonClient`

Creates a `TwitterOpenapiPythonClient` instance from cookies.

### `get_guest_client(self) -> TwitterOpenapiPythonClient`

Creates a `TwitterOpenapiPythonClient` instance for guest users.
