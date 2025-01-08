# InitialStateApiUtilsRaw

This class represents the raw initial state data from the API.

## Attributes

- `initial_state`: A dictionary containing the initial state data.
- `meta_data`: A dictionary containing the meta data.

# InitialStateApiUtilsResponse

This class represents the response from the initial state API.

## Attributes

- `raw`: An instance of `InitialStateApiUtilsRaw` containing the raw data.
- `user`: An optional instance of `twitter.UserLegacy` representing the user.
- `session`: An optional instance of `twitter.Session` representing the session.
