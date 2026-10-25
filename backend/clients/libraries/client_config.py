"""Shared connection options for the local tool clients."""
import argparse
import os
from urllib.parse import urlsplit


def get_backend_url() -> str:
    parser = argparse.ArgumentParser(description="Connect a local tool client to BBAgent.")
    parser.add_argument(
        "--url",
        default=os.getenv("BBAGENT_API_URL", "http://localhost:8000"),
        help="Backend URL (default: BBAGENT_API_URL or http://localhost:8000).",
    )
    value = parser.parse_args().url.strip().rstrip("/")
    parsed = urlsplit(value)
    if (parsed.scheme not in {"http", "https"} or not parsed.netloc
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        parser.error("--url must be an HTTP(S) URL without credentials, query or fragment.")
    return value
