"""
NanoClaw Executor Service - Main Entry Point.

Intelligent test executor with browser health monitoring.
"""

import os
import sys
import logging
import uvicorn

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from executor.api import app


def setup_logging():
    """Configure logging for the executor service."""
    log_level = os.getenv("EXECUTOR_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Main entry point for the executor service."""
    setup_logging()
    logger = logging.getLogger(__name__)

    host = os.getenv("EXECUTOR_HOST", "0.0.0.0")
    port = int(os.getenv("EXECUTOR_PORT", "8001"))

    logger.info(f"Starting NanoClaw Executor service on {host}:{port}")

    try:
        uvicorn.run(
            "executor.api:app",
            host=host,
            port=port,
            reload=False,  # Don't reload in production
            log_level=os.getenv("EXECUTOR_LOG_LEVEL", "info").lower(),
        )
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
