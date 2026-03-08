"""
NanoClaw Monitor Service - Main Entry Point.

Browser health monitoring sidecar that collects real-time metrics
during test execution.
"""

import os
import sys
import logging
import uvicorn

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitor.api import app


def setup_logging():
    """Configure logging for the monitor service."""
    log_level = os.getenv("MONITOR_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Main entry point for the monitor service."""
    setup_logging()
    logger = logging.getLogger(__name__)

    host = os.getenv("MONITOR_HOST", "0.0.0.0")
    port = int(os.getenv("MONITOR_PORT", "8002"))

    logger.info(f"Starting NanoClaw Monitor service on {host}:{port}")

    try:
        uvicorn.run(
            "monitor.api:app",
            host=host,
            port=port,
            reload=False,  # Don't reload in production
            log_level=os.getenv("MONITOR_LOG_LEVEL", "info").lower(),
        )
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
