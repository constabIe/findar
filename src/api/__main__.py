"""
CLI entry point for running the API server.

Usage:
    uv run -m src.api
"""

import os

import dotenv
import uvicorn


def main():
    dotenv.load_dotenv()

    """Run the API server with uvicorn."""
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=int(os.getenv("API_PORT", -1)),
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
