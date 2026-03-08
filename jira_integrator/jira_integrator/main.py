"""
NanoClaw Jira Integrator Service - Main Entry Point.

Posts test results and evidence packages to Jira tickets.
"""

import os
import sys
import logging
import uvicorn

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jira_integrator.api import app


def setup_logging():
    """Configure logging for the Jira integrator service."""
    log_level = os.getenv("JIRA_INTEGRATOR_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Main entry point for the Jira integrator service."""
    setup_logging()
    logger = logging.getLogger(__name__)

    host = os.getenv("JIRA_INTEGRATOR_HOST", "0.0.0.0")
    port = int(os.getenv("JIRA_INTEGRATOR_PORT", "8003"))

    logger.info(f"Starting NanoClaw Jira Integrator service on {host}:{port}")

    try:
        uvicorn.run(
            "jira_integrator.api:app",
            host=host,
            port=port,
            reload=False,
            log_level=os.getenv("JIRA_INTEGRATOR_LOG_LEVEL", "info").lower(),
        )
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
