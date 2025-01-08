# TwitterApiUtilsRaw

This class represents the raw response from the Twitter API.

## Attributes

- `response`: An instance of `twitter.ApiResponse` containing the raw response data.

# TwitterApiUtilsResponse

This class represents a generic response from the Twitter API.

## Attributes

- `raw`: An instance of `TwitterApiUtilsRaw` containing the raw response data.
- `data`: The data payload of the response, which can be of any type.
- `header`: An instance of `ApiUtilsHeader` containing the response headers.
