"""
Browser Context Manager for NanoClaw Role 2.

Manages isolated Playwright browser contexts for each test execution.
Ensures a fresh browser state (no cookies, no cache) for every test.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
)

logger = logging.getLogger(__name__)


class BrowserContextManager:
    """
    Creates and manages isolated Playwright browser contexts.

    Each test run gets:
    - A fresh browser context (no cache, no cookies, no shared state)
    - Optional Playwright trace recording for forensic replay
    - Optional screenshot capture on failure
    """

    def __init__(
        self,
        headless: bool = True,
        trace_enabled: bool = True,
        slow_mo_ms: int = 0,
        results_dir: str = "./shared/results",
    ):
        """
        Initialise the context manager.

        Args:
            headless: Run browser without a visible window.
            trace_enabled: Record a Playwright trace for replay.
            slow_mo_ms: Add deliberate delay (ms) between actions.
            results_dir: Base directory for evidence output.
        """
        self.headless = headless
        self.trace_enabled = trace_enabled
        self.slow_mo_ms = slow_mo_ms
        self.results_dir = results_dir

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def create_context(self, execution_id: str) -> tuple[Browser, BrowserContext, Page]:
        """
        Launch a fresh browser and create an isolated context.

        Args:
            execution_id: Used to scope trace/screenshot paths.

        Returns:
            Tuple of (browser, context, page) ready for use.
        """
        self._playwright = await async_playwright().start()

        logger.info("Launching Chromium browser (headless=%s)", self.headless)
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo_ms,
            args=[
                "--disable-dev-shm-usage",   # stability inside Docker
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )

        # Each context is completely isolated
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=False,
            java_script_enabled=True,
        )

        if self.trace_enabled:
            await self._context.tracing.start(
                screenshots=True,
                snapshots=True,
                sources=True,
            )
            logger.info("Playwright trace recording started")

        self._page = await self._context.new_page()
        logger.info("Browser context created for execution %s", execution_id)

        return self._browser, self._context, self._page

    async def stop_and_save_trace(self, execution_id: str) -> Optional[str]:
        """
        Stop tracing and save the trace zip to the results directory.

        Args:
            execution_id: Used to construct the output filename.

        Returns:
            Absolute path to the saved trace zip, or None if tracing was disabled.
        """
        if not (self.trace_enabled and self._context):
            return None

        trace_dir = Path(self.results_dir) / execution_id
        trace_dir.mkdir(parents=True, exist_ok=True)
        trace_path = str(trace_dir / "trace.zip")

        await self._context.tracing.stop(path=trace_path)
        logger.info("Trace saved to %s", trace_path)
        return trace_path

    async def take_screenshot(self, execution_id: str, label: str = "failure") -> Optional[str]:
        """
        Capture a full-page screenshot.

        Args:
            execution_id: Used to scope the output directory.
            label: Descriptive name for the screenshot file.

        Returns:
            Path to the saved screenshot, or None on error.
        """
        if not self._page:
            return None

        screenshot_dir = Path(self.results_dir) / execution_id / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = str(screenshot_dir / f"{label}.png")

        try:
            await self._page.screenshot(path=screenshot_path, full_page=True)
            logger.info("Screenshot saved to %s", screenshot_path)
            return screenshot_path
        except Exception as exc:
            logger.error("Failed to capture screenshot: %s", exc)
            return None

    async def close(self) -> None:
        """Close the page, context, browser, and Playwright instance cleanly."""
        try:
            if self._page and not self._page.is_closed():
                await self._page.close()
        except Exception as exc:
            logger.warning("Error closing page: %s", exc)

        try:
            if self._context:
                await self._context.close()
        except Exception as exc:
            logger.warning("Error closing context: %s", exc)

        try:
            if self._browser:
                await self._browser.close()
        except Exception as exc:
            logger.warning("Error closing browser: %s", exc)

        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception as exc:
            logger.warning("Error stopping Playwright: %s", exc)

        logger.info("Browser context cleaned up")
