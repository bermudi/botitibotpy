"""Main entry point for the CLI."""

import sys
from . import main

def run_cli():
    """Run the CLI application."""
    sys.exit(main())

if __name__ == '__main__':
    run_cli() 