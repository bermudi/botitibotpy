# PostApiUtils

This class provides utility functions for the POST API endpoints.

## Methods

### `__init__(self, api: twitter.PostApi, flag: ParamType)`

Initializes the utility with an API client and a flag.

- `api`: An instance of `twitter.PostApi`.
- `flag`: A dictionary containing flag values.

### `post_create_tweet(self, tweet_text: str, media_ids: Optional[list[str]] = None, tagged_users: Optional[list[list[str]]] = None, in_reply_to_tweet_id: Optional[str] = None, attachment_url: Optional[str] = None, conversation_control: Optional[str] = None) -> ResponseType[models.CreateTweetResponse]`

Creates a new tweet.

- `tweet_text`: The text of the tweet.
- `media_ids`: A list of media IDs to attach to the tweet.
- `tagged_users`: A list of lists of user IDs to tag in the tweet.
- `in_reply_to_tweet_id`: The ID of the tweet to reply to.
- `attachment_url`: The URL of an attachment.
- `conversation_control`: The conversation control setting.

### `post_delete_tweet(self, tweet_id: str) -> ResponseType[models.DeleteTweetResponse]`

Deletes a tweet.

- `tweet_id`: The ID of the tweet to delete.

### `post_create_retweet(self, tweet_id: str) -> ResponseType[models.CreateRetweetResponse]`

Creates a retweet.

- `tweet_id`: The ID of the tweet to retweet.

### `post_delete_retweet(self, source_tweet_id: str) -> ResponseType[models.DeleteRetweetResponse]`

Deletes a retweet.

- `source_tweet_id`: The ID of the source tweet to delete the retweet from.

### `post_favorite_tweet(self, tweet_id: str) -> ResponseType[models.FavoriteTweetResponse]`

Favorites a tweet.

- `tweet_id`: The ID of the tweet to favorite.

### `post_unfavorite_tweet(self, tweet_id: str) -> ResponseType[models.UnfavoriteTweetResponse]`

Unfavorites a tweet.

- `tweet_id`: The ID of the tweet to unfavorite.
