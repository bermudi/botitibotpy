# ApiUtilsRaw

This class represents the raw data for API responses related to timelines.

## Attributes

- `instruction`: A list of `models.InstructionUnion` objects.
- `entry`: A list of `models.TimelineAddEntry` objects.

# CursorApiUtilsResponse

This class represents the cursor information for paginated API responses.

## Attributes

- `bottom`: An optional `models.TimelineTimelineCursor` object representing the bottom cursor.
- `top`: An optional `models.TimelineTimelineCursor` object representing the top cursor.

# TweetApiUtilsData

This class represents the data for a tweet in a timeline.

## Attributes

- `raw`: A `models.ItemResult` object containing the raw tweet data.
- `tweet`: A `models.Tweet` object representing the tweet.
- `user`: A `models.User` object representing the user who posted the tweet.
- `replies`: A list of `TweetApiUtilsData` objects representing replies to the tweet.
- `quoted`: An optional `TweetApiUtilsData` object representing a quoted tweet.
- `retweeted`: An optional `TweetApiUtilsData` object representing a retweeted tweet.
- `promoted_metadata`: An optional dictionary containing promoted metadata.

# UserApiUtilsData

This class represents the data for a user in a timeline.

## Attributes

- `raw`: A `models.UserResults` object containing the raw user data.
- `user`: A `models.User` object representing the user.

# TimelineApiUtilsResponse

This class represents a generic response for timeline-related API endpoints.

## Attributes

- `raw`: An `ApiUtilsRaw` object containing the raw timeline data.
- `cursor`: A `CursorApiUtilsResponse` object containing the cursor information.
- `data`: A list of type `T` representing the timeline data.
