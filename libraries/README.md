# Libraries Cog

A utility cog that provides shared libraries and common functionality for other tanx-cogs.

## Purpose

This cog serves as a central repository for reusable utilities that multiple cogs need to access, such as:

- **WindmillClient**: A client for interacting with Windmill API for various operations (image processing, etc.)

## Installation

```
[p]load libraries
```

## Usage

This is a backend utility cog with no user-facing commands. Other cogs can import and use the provided utilities.

### For Developers

To use the WindmillClient in your cog:

```python
from libraries.windmill_client import WindmillClient

# In your cog
client = WindmillClient()
# Use the client...
```

## Requirements

- aiohttp

## Configuration

The WindmillClient uses the following environment variables:

- `WINDMILL_BASE_URL`: Base URL for the Windmill instance
- `WINDMILL_TOKEN`: Authentication token for Windmill API

## Dependencies

This cog must be loaded before any other cogs that depend on it (like the LLM cog).
