# InitialStateApiUtils

This class provides utility functions for the initial state API endpoint.

## Methods

### `__init__(self, api: twitter.ApiClient)`

Initializes the utility with an API client.

- `api`: An instance of `twitter.ApiClient`.

### `request(self, url: str) -> HTTPResponse`

A generic request method that calls an API function.

- `url`: The URL to request.

### `get_initial_state(self, url: str) -> InitialStateApiUtilsResponse`

Retrieves the initial state from a given URL.

- `url`: The URL to fetch the initial state from.
