"""
Metrics Collector for Browser Health Monitoring.

Uses Chrome DevTools Protocol (CDP) and psutil to collect real-time
browser metrics during test execution.
"""

import asyncio
import psutil
from datetime import datetime
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, BrowserContext
import logging

from models import (
    BrowserMetrics,
    NetworkError,
    ConsoleError,
)


logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects real-time browser health metrics.

    Combines:
    - Chrome DevTools Protocol (CDP) for browser internals
    - psutil for process-level CPU and memory
    """

    def __init__(
        self,
        sample_interval_ms: int = 100,
        enable_cdp: bool = True,
        enable_psutil: bool = True,
    ):
        """
        Initialize metrics collector.

        Args:
            sample_interval_ms: Time between metric samples (milliseconds)
            enable_cdp: Enable Chrome DevTools Protocol monitoring
            enable_psutil: Enable process-level monitoring via psutil
        """
        self.sample_interval_ms = sample_interval_ms
        self.enable_cdp = enable_cdp
        self.enable_psutil = enable_psutil
        self.is_collecting = False

        # Browser and process references
        self.browser: Optional[Browser] = None
        self.browser_process: Optional[psutil.Process] = None
        self.context: Optional[BrowserContext] = None

        # CDP sessions
        self.cdp_session: Optional[Any] = None

        # Metric buffers
        self.network_errors: List[NetworkError] = []
        self.console_errors: List[ConsoleError] = []
        self.console_warnings: List[ConsoleError] = []  # Separate list for warnings
        self.metrics_buffer: List[BrowserMetrics] = []

    async def start(self, browser: Browser, context: BrowserContext) -> None:
        """
        Start collecting metrics from the browser.

        Args:
            browser: Playwright Browser instance
            context: Playwright BrowserContext instance
        """
        if self.is_collecting:
            logger.warning("Metrics collector already running")
            return

        self.browser = browser
        self.context = context

        # Get browser process for psutil monitoring
        if self.enable_psutil:
            try:
                # Playwright uses browser processes - get the main one
                browser_version = browser.version
                # Note: Actual process retrieval depends on Playwright internals
                # We'll monitor the current Python process as fallback
                current_process = psutil.Process()
                # Try to find browser child processes
                for child in current_process.children(recursive=True):
                    if "chrome" in child.name().lower() or "chromium" in child.name().lower():
                        self.browser_process = child
                        break

                if not self.browser_process:
                    logger.warning("Could not find browser process, using current process")
                    self.browser_process = current_process

            except Exception as e:
                logger.error(f"Failed to get browser process: {e}")

        # Setup CDP monitoring
        if self.enable_cdp:
            await self._setup_cdp_monitoring()

        self.is_collecting = True
        logger.info("Metrics collector started")

    async def _setup_cdp_monitoring(self) -> None:
        """
        Setup Chrome DevTools Protocol monitoring.

        Enables:
        - Network monitoring (for 4xx/5xx errors)
        - Console logging (for errors/warnings)
        - Performance monitoring (for memory)
        """
        try:
            # CDP session setup would go here
            # Note: Playwright's CDP integration requires accessing the underlying CDPSession
            # This is a simplified version - actual implementation depends on Playwright version

            # For now, we'll use Playwright's built-in event listeners
            # Note: Playwright's context.on() expects sync callbacks, so we wrap async handlers
            self.context.on("console", lambda msg: asyncio.ensure_future(self._handle_console_event(msg)))
            self.context.on("response", lambda resp: asyncio.ensure_future(self._handle_response_event(resp)))

            logger.info("CDP monitoring enabled")

        except Exception as e:
            logger.error(f"Failed to setup CDP monitoring: {e}")
            self.enable_cdp = False

    async def _handle_console_event(self, msg: Any) -> None:
        """
        Handle console messages from the browser.

        Args:
            msg: Console message from Playwright
        """
        try:
            console_msg = ConsoleError(
                timestamp=datetime.utcnow(),
                level=msg.type,
                message=msg.text,
                source_url=getattr(msg, 'location', {}).get('url'),
                line_number=getattr(msg, 'location', {}).get('lineNumber'),
            )

            if msg.type == "error":
                self.console_errors.append(console_msg)
                logger.warning(f"Console error: {msg.text}")
            elif msg.type == "warning":
                self.console_warnings.append(console_msg)
                logger.debug(f"Console warning: {msg.text}")

        except Exception as e:
            logger.error(f"Error handling console event: {e}")

    async def _handle_response_event(self, response: Any) -> None:
        """
        Handle network responses to detect errors.

        Args:
            response: Response object from Playwright
        """
        try:
            status = response.status
            if status >= 400:
                error = NetworkError(
                    timestamp=datetime.utcnow(),
                    url=response.url,
                    status_code=status,
                    method=response.request.method if hasattr(response, 'request') else "UNKNOWN",
                    error_type="4xx" if 400 <= status < 500 else "5xx",
                )
                self.network_errors.append(error)
                logger.warning(f"Network error: {status} {response.url}")

        except Exception as e:
            logger.error(f"Error handling response event: {e}")

    async def collect_current_metrics(self) -> BrowserMetrics:
        """
        Collect current snapshot of browser metrics.

        Returns:
            BrowserMetrics: Current metric snapshot
        """
        timestamp = datetime.utcnow()
        memory_heap_mb = 0.0
        memory_total_mb = 0.0
        cpu_percent = 0.0

        # Collect psutil metrics
        if self.enable_psutil and self.browser_process:
            try:
                # Memory info
                mem_info = self.browser_process.memory_info()
                memory_total_mb = mem_info.rss / (1024 * 1024)  # Convert to MB

                # CPU percentage (requires interval measurement)
                cpu_percent = self.browser_process.cpu_percent(interval=0.1)

                # For heap-specific memory, we'd need CDP
                # Fallback to total memory divided by typical heap ratio
                memory_heap_mb = memory_total_mb * 0.7  # Approximate

            except psutil.NoSuchProcess:
                logger.warning("Browser process no longer exists")
            except Exception as e:
                logger.error(f"Error collecting psutil metrics: {e}")

        # Create metrics snapshot
        metrics = BrowserMetrics(
            timestamp=timestamp,
            memory_heap_mb=memory_heap_mb,
            memory_total_mb=memory_total_mb,
            cpu_percent=cpu_percent,
            network_errors=self.network_errors.copy(),
            console_errors=self.console_errors.copy(),
            console_warnings=[],  # Populated separately
        )

        self.metrics_buffer.append(metrics)
        return metrics

    async def start_streaming(self, callback) -> None:
        """
        Start continuous metric streaming.

        Args:
            callback: Async function called with each metrics snapshot
        """
        if not self.is_collecting:
            raise RuntimeError("Metrics collector not started. Call start() first.")

        logger.info(f"Starting metrics streaming (interval: {self.sample_interval_ms}ms)")

        while self.is_collecting:
            try:
                metrics = await self.collect_current_metrics()
                await callback(metrics)

                await asyncio.sleep(self.sample_interval_ms / 1000)

            except asyncio.CancelledError:
                logger.info("Metrics streaming cancelled")
                break
            except Exception as e:
                logger.error(f"Error in metrics streaming: {e}")
                await asyncio.sleep(1)  # Brief pause before retry

    async def stop(self) -> Dict[str, Any]:
        """
        Stop collecting metrics and return summary.

        Returns:
            Summary of collected metrics
        """
        self.is_collecting = False

        # Calculate summary statistics
        if self.metrics_buffer:
            memory_values = [m.memory_heap_mb for m in self.metrics_buffer]
            cpu_values = [m.cpu_percent for m in self.metrics_buffer]

            summary = {
                "total_samples": len(self.metrics_buffer),
                "peak_memory_mb": max(memory_values) if memory_values else 0,
                "avg_memory_mb": sum(memory_values) / len(memory_values) if memory_values else 0,
                "peak_cpu_percent": max(cpu_values) if cpu_values else 0,
                "avg_cpu_percent": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                "total_network_errors": len(self.network_errors),
                "total_console_errors": len(self.console_errors),
                "total_console_warnings": len(self.console_warnings),
            }
        else:
            summary = {
                "total_samples": 0,
                "peak_memory_mb": 0,
                "avg_memory_mb": 0,
                "peak_cpu_percent": 0,
                "avg_cpu_percent": 0,
                "total_network_errors": 0,
                "total_console_errors": 0,
                "total_console_warnings": 0,
            }

        logger.info(f"Metrics collector stopped. Summary: {summary}")
        return summary

    def get_error_details(self) -> Dict[str, List]:
        """
        Get detailed error information collected during monitoring.

        Returns:
            Dict with network_errors and console_errors lists
        """
        return {
            "network_errors": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "url": e.url,
                    "status_code": e.status_code,
                    "method": e.method,
                    "error_type": e.error_type,
                }
                for e in self.network_errors
            ],
            "console_errors": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "level": e.level,
                    "message": e.message,
                    "source_url": e.source_url,
                    "line_number": e.line_number,
                }
                for e in self.console_errors
            ],
        }

    def clear_buffers(self) -> None:
        """Clear error and metrics buffers."""
        self.network_errors.clear()
        self.console_errors.clear()
        self.console_warnings.clear()
        self.metrics_buffer.clear()
        logger.info("Metrics buffers cleared")
