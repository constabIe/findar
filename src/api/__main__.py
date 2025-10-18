"""
CLI entry point for running the API server.

Usage:
    uv run -m src.api
"""

import uvicorn


def main():
    """Run the API server with uvicorn."""
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
