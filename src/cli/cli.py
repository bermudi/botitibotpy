import click
from src.content_generation.content_generator import ContentGenerator
from src.data_handling.data_handler import parse_webpage, read_rss_feed
from src.social_media_integration.bluesky_integration import BlueskyClient
from src.social_media_integration.twitter_integration import TwitterClient
import json

@click.group()
def cli():
    """Social Media Content Creation Framework CLI"""
    pass

@cli.command()
@click.argument('prompt')
def generate(prompt):
    """Generate content using LlamaIndex"""
    generator = ContentGenerator()
    content = generator.generate_content(prompt)
    click.echo(f"Generated content:\n{content}")

@cli.command()
@click.argument('url')
def parse_webpage(url):
    """Parse a web page for content ideas"""
    content = parse_webpage(url)
    click.echo(f"Parsed content:\n{content}")

@cli.command()
@click.argument('url')
def read_rss(url):
    """Read an RSS feed for content ideas"""
    entries = read_rss_feed(url)
    click.echo(f"RSS feed entries:\n{json.dumps(entries, indent=2)}")

@cli.group()
def bluesky():
    """Interact with Bluesky"""
    pass

@bluesky.command()
@click.argument('identifier')
@click.argument('password')
def auth(identifier, password):
    """Authenticate with Bluesky"""
    client = BlueskyClient()
    if client.authenticate(identifier, password):
        click.echo("Successfully authenticated with Bluesky")
    else:
        click.echo("Failed to authenticate with Bluesky")

@bluesky.command()
@click.argument('text')
def post(text):
    """Create a Bluesky post"""
    client = BlueskyClient()
    result = client.create_post(text)
    if 'error' in result:
        click.echo(f"Error creating post: {result['error']}")
    else:
        click.echo(f"Successfully created post: {result['uri']}")

@bluesky.command()
@click.argument('post_uri')
def comments(post_uri):
    """Get Bluesky post comments"""
    client = BlueskyClient()
    comments = client.get_comments(post_uri)
    click.echo(f"Comments:\n{json.dumps(comments, indent=2)}")

@bluesky.command()
@click.argument('comment_uri')
@click.argument('text')
def respond(comment_uri, text):
    """Respond to a Bluesky comment"""
    client = BlueskyClient()
    result = client.respond_to_comment(comment_uri, text)
    if 'error' in result:
        click.echo(f"Error responding to comment: {result['error']}")
    else:
        click.echo(f"Successfully responded to comment: {result['uri']}")

@cli.group()
def twitter():
    """Interact with Twitter"""
    pass

@twitter.command()
@click.argument('api_key')
@click.argument('api_secret')
@click.argument('access_token')
@click.argument('access_secret')
def auth(api_key, api_secret, access_token, access_secret):
    """Authenticate with Twitter"""
    client = TwitterClient()
    if client.authenticate(api_key, api_secret, access_token, access_secret):
        click.echo("Successfully authenticated with Twitter")
    else:
        click.echo("Failed to authenticate with Twitter")

@twitter.command()
@click.argument('text')
def tweet(text):
    """Create a Twitter tweet"""
    client = TwitterClient()
    result = client.create_tweet(text)
    if 'error' in result:
        click.echo(f"Error creating tweet: {result['error']}")
    else:
        click.echo(f"Successfully created tweet: {result['id']}")

@twitter.command()
@click.argument('tweet_id')
def tweet_comments(tweet_id):
    """Get Twitter tweet comments"""
    client = TwitterClient()
    comments = client.get_tweet_comments(tweet_id)
    click.echo(f"Comments:\n{json.dumps(comments, indent=2)}")

@twitter.command()
@click.argument('comment_id')
@click.argument('text')
def tweet_respond(comment_id, text):
    """Respond to a Twitter comment"""
    client = TwitterClient()
    result = client.respond_to_tweet_comment(comment_id, text)
    if 'error' in result:
        click.echo(f"Error responding to comment: {result['error']}")
    else:
        click.echo(f"Successfully responded to comment: {result['id']}")

if __name__ == '__main__':
    cli()
