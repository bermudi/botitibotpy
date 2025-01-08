# API Utility Functions

This file contains various utility functions used in the Twitter API client.

## Functions

### `flat(matrix: List[List[T]]) -> List[T]`

Flattens a 2D list into a 1D list.

- `matrix`: The 2D list to flatten.

### `non_nullable(x: Optional[T]) -> T`

Returns the value if it's not None, otherwise raises an exception.

- `x`: The optional value.

### `non_nullable_list(x: List[Optional[T]]) -> List[T]`

Filters out None values from a list.

- `x`: The list of optional values.

### `get_kwargs(flag: ParamType, additional: ParamType) -> ParamType`

Constructs keyword arguments for API calls.

- `flag`: The flag parameters.
- `additional`: Additional parameters.

### `get_legacy_kwargs(flag: ParamType, additional: ParamType) -> ParamType`

Constructs keyword arguments for legacy API calls.

- `flag`: The flag parameters.
- `additional`: Additional parameters.

### `error_check(data: Optional[T], error: Optional[List[models.ErrorResponse]]) -> T`

Checks for errors in the API response and returns the data or raises an exception.

- `data`: The data from the API response.
- `error`: A list of errors from the API response.

### `instruction_to_entry(input: List[models.InstructionUnion]) -> List[models.TimelineAddEntry]`

Converts a list of instructions to a list of timeline entries.

- `input`: A list of `models.InstructionUnion` objects.

### `tweet_entries_converter(input: List[models.TimelineAddEntry]) -> List[TweetApiUtilsData]`

Converts a list of timeline entries to a list of `TweetApiUtilsData` objects.

- `input`: A list of `models.TimelineAddEntry` objects.

### `user_or_null_converter(user: models.UserUnion) -> Optional[models.User]`

Converts a `UserUnion` to a `User` object, or returns None if the user is not found.

- `user`: A `models.UserUnion` object.

### `build_tweet_api_utils(result: models.ItemResult, promoted_metadata: Optional[dict[str, Any]] = None, reply: Optional[List[models.TimelineTweet]] = None) -> Optional[TweetApiUtilsData]`

Builds a `TweetApiUtilsData` object from a tweet result.

- `result`: A `models.ItemResult` object.
- `promoted_metadata`: Optional promoted metadata.
- `reply`: Optional list of replies.

### `tweet_results_converter(tweetResults: models.ItemResult) -> Optional[models.Tweet]`

Converts a tweet result to a `Tweet` object.

- `tweetResults`: A `models.ItemResult` object.

### `user_entries_converter(item: list[models.TimelineAddEntry]) -> list[models.UserResults]`

Converts a list of timeline entries to a list of `UserResults` objects.

- `item`: A list of `models.TimelineAddEntry` objects.

### `user_result_converter(item: list[models.UserResults]) -> List[UserApiUtilsData]`

Converts a list of `UserResults` objects to a list of `UserApiUtilsData` objects.

- `item`: A list of `models.UserResults` objects.

### `entries_cursor(item: List[models.TimelineAddEntry]) -> CursorApiUtilsResponse`

Extracts cursor information from a list of timeline entries.

- `item`: A list of `models.TimelineAddEntry` objects.

### `build_cursor(list: list[models.TimelineTimelineCursor]) -> CursorApiUtilsResponse`

Builds a `CursorApiUtilsResponse` object from a list of timeline cursors.

- `list`: A list of `models.TimelineTimelineCursor` objects.

### `build_header(headers: Dict[str, str]) -> ApiUtilsHeader`

Builds an `ApiUtilsHeader` object from a dictionary of headers.

- `headers`: A dictionary of headers.

### `build_response(response: twitter.ApiResponse, data: T1) -> TwitterApiUtilsResponse[T1]`

Builds a `TwitterApiUtilsResponse` object from an API response and data.

- `response`: A `twitter.ApiResponse` object.
- `data`: The data payload of the response.
