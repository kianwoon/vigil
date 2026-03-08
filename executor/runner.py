"""
Test Runner for NanoClaw Role 2.

Orchestrates the full test execution lifecycle:
  1. Resolve script from shared volume
  2. Spawn fresh browser context via BrowserContextManager
  3. Start monitor sidecar metrics collection (WebSocket)
  4. Execute pytest with --json-report and --tracing
  5. Collect health metrics and compute grade
  6. Package evidence (CSV, logs, trace, screenshots)
  7. Return ExecutionResult for Jira update and notification
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

import websockets

from models import (
    BrowserMetrics,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthAnalysis,
    HealthGrade,
    TestResult,
)
from health_analyzer import HealthAnalyzer
from context_manager import BrowserContextManager

logger = logging.getLogger(__name__)


class TestRunner:
    """
    Executes Playwright/pytest test scripts with concurrent health monitoring.

    Connects to the monitor sidecar via WebSocket to stream real-time
    browser metrics while pytest runs in a subprocess.
    """

    def __init__(
        self,
        shared_scripts_dir: str,
        shared_results_dir: str,
        monitor_ws_url: str = "ws://monitor:8002",
    ):
        """
        Initialise the test runner.

        Args:
            shared_scripts_dir: Directory containing test scripts from Role 1.
            shared_results_dir: Directory for evidence output.
            monitor_ws_url: WebSocket URL of the monitor sidecar.
        """
        self.shared_scripts_dir = shared_scripts_dir
        self.shared_results_dir = shared_results_dir
        self.monitor_ws_url = monitor_ws_url
        self.health_analyzer = HealthAnalyzer(
            memory_leak_threshold_mb=float(
                os.getenv("HEALTH_MEMORY_LEAK_THRESHOLD_MB", "100")
            ),
            memory_leak_window_seconds=int(
                os.getenv("HEALTH_MEMORY_LEAK_WINDOW_SECONDS", "60")
            ),
            cpu_warning_percent=float(
                os.getenv("HEALTH_CPU_WARNING_PERCENT", "60")
            ),
            cpu_critical_percent=float(
                os.getenv("HEALTH_CPU_CRITICAL_PERCENT", "80")
            ),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Run a test script end-to-end and return a complete ExecutionResult.

        Args:
            request: Execution parameters (job_id, script_path, jira_ticket, …).

        Returns:
            ExecutionResult populated with test outcome, health grade, and
            evidence package paths.
        """
        execution_id = f"exec-{uuid4().hex[:12]}"
        started_at = datetime.utcnow()

        logger.info(
            "Starting execution %s for job %s (Jira: %s)",
            execution_id,
            request.job_id,
            request.jira_ticket,
        )

        # Prepare output directories
        results_dir = Path(self.shared_results_dir) / execution_id
        results_dir.mkdir(parents=True, exist_ok=True)

        # Resolve script path
        script_path = self._resolve_script_path(request.script_path)
        if not script_path:
            return self._error_result(
                execution_id,
                request,
                started_at,
                f"Script not found: {request.script_path}",
            )

        # Collect metrics concurrently while pytest runs
        metrics: List[BrowserMetrics] = []
        log_lines: List[str] = []

        try:
            test_passed, pytest_output, trace_path, screenshot_path = (
                await asyncio.wait_for(
                    self._run_with_monitoring(
                        request,
                        execution_id,
                        script_path,
                        str(results_dir),
                        metrics,
                        log_lines,
                    ),
                    timeout=request.timeout_seconds,
                )
            )
        except asyncio.TimeoutError:
            logger.error("Execution %s timed out after %ss", execution_id, request.timeout_seconds)
            return self._error_result(
                execution_id,
                request,
                started_at,
                f"Execution timed out after {request.timeout_seconds}s",
                status=ExecutionStatus.TIMEOUT,
            )
        except Exception as exc:
            logger.exception("Unexpected error in execution %s", execution_id)
            return self._error_result(execution_id, request, started_at, str(exc))

        completed_at = datetime.utcnow()
        duration = (completed_at - started_at).total_seconds()

        # Analyse health
        health_analysis = self.health_analyzer.analyze(metrics)
        if not test_passed:
            # Downgrade to CRITICAL if the test itself failed
            health_analysis = HealthAnalysis(
                grade=HealthGrade.CRITICAL,
                issues=["Test execution failed (pytest exit code != 0)"] + health_analysis.issues,
                warnings=health_analysis.warnings,
                metrics_summary=health_analysis.metrics_summary,
            )

        # Package evidence files
        logs_path = self._save_logs(str(results_dir), pytest_output, log_lines)
        metrics_path = self._save_metrics_csv(str(results_dir), metrics)

        # Aggregate peak values
        peak_memory = max((m.memory_heap_mb for m in metrics), default=0.0)
        peak_cpu = max((m.cpu_percent for m in metrics), default=0.0)
        total_net_errors = sum(len(m.network_errors) for m in metrics)
        total_con_errors = sum(len(m.console_errors) for m in metrics)
        total_con_warnings = sum(len(m.console_warnings) for m in metrics)

        result = ExecutionResult(
            execution_id=execution_id,
            job_id=request.job_id,
            jira_ticket=request.jira_ticket,
            status=ExecutionStatus.COMPLETED,
            test_result=TestResult.PASS if test_passed else TestResult.FAIL,
            health_analysis=health_analysis,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            peak_memory_mb=peak_memory,
            peak_cpu_percent=peak_cpu,
            total_network_errors=total_net_errors,
            total_console_errors=total_con_errors,
            total_console_warnings=total_con_warnings,
            trace_path=trace_path,
            logs_path=logs_path,
            metrics_path=metrics_path,
            screenshot_path=screenshot_path,
        )

        logger.info(
            "Execution %s completed: %s | Health: %s | Duration: %.1fs",
            execution_id,
            result.test_result.value,
            result.health_analysis.grade.value,
            duration,
        )
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _run_with_monitoring(
        self,
        request: ExecutionRequest,
        execution_id: str,
        script_path: str,
        results_dir: str,
        metrics: List[BrowserMetrics],
        log_lines: List[str],
    ):
        """Run pytest and metrics collection concurrently."""
        json_report_path = os.path.join(results_dir, "report.json")

        # Build pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            script_path,
            f"--json-report",
            f"--json-report-file={json_report_path}",
            "--tb=short",
            "-v",
        ]

        if request.trace_enabled:
            cmd += ["--tracing=on"]

        logger.info("Running pytest: %s", " ".join(cmd))

        # Start pytest subprocess
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=os.path.dirname(script_path),
        )

        # Collect metrics from the monitor sidecar concurrently
        metrics_task = asyncio.create_task(
            self._stream_metrics(execution_id, metrics)
        )

        # Read subprocess output
        stdout_bytes, _ = await process.communicate()
        stdout_text = stdout_bytes.decode(errors="replace")
        log_lines.extend(stdout_text.splitlines())

        # Stop metrics collection
        metrics_task.cancel()
        try:
            await metrics_task
        except asyncio.CancelledError:
            pass

        test_passed = process.returncode == 0

        # Extract trace path from results dir (pytest-playwright writes it there)
        trace_path: Optional[str] = None
        trace_candidate = os.path.join(results_dir, "trace.zip")
        if os.path.exists(trace_candidate):
            trace_path = trace_candidate

        # Screenshot on failure
        screenshot_path: Optional[str] = None
        screenshot_dir = os.path.join(results_dir, "screenshots")
        if os.path.isdir(screenshot_dir):
            shots = list(Path(screenshot_dir).glob("*.png"))
            if shots:
                screenshot_path = str(shots[0])

        return test_passed, stdout_text, trace_path, screenshot_path

    async def _stream_metrics(
        self,
        execution_id: str,
        metrics: List[BrowserMetrics],
    ) -> None:
        """
        Connect to the monitor sidecar WebSocket and collect metrics.

        Silently continues if the monitor is unavailable (e.g. local dev).
        """
        ws_url = f"{self.monitor_ws_url}/ws/metrics"
        try:
            async with websockets.connect(ws_url, open_timeout=5) as ws:
                logger.info("Connected to monitor at %s", ws_url)
                async for raw in ws:
                    try:
                        data = json.loads(raw)
                        metric = BrowserMetrics(
                            timestamp=datetime.fromisoformat(
                                data.get("timestamp", datetime.utcnow().isoformat())
                            ),
                            memory_heap_mb=float(data.get("memory_heap_mb", 0)),
                            memory_total_mb=float(data.get("memory_total_mb", 0)),
                            cpu_percent=float(data.get("cpu_percent", 0)),
                            network_errors=data.get("network_errors", []),
                            console_errors=data.get("console_errors", []),
                            console_warnings=data.get("console_warnings", []),
                        )
                        metrics.append(metric)
                    except Exception as parse_err:
                        logger.debug("Failed to parse metric frame: %s", parse_err)
        except asyncio.CancelledError:
            raise  # let the task cancellation propagate
        except Exception as exc:
            logger.warning(
                "Monitor sidecar unavailable (%s), continuing without metrics", exc
            )

    def _resolve_script_path(self, script_path: str) -> Optional[str]:
        """
        Return an absolute path to the test script.

        Checks the raw path first, then tries looking it up inside the
        shared scripts directory.
        """
        # Absolute or relative path given directly
        if os.path.isabs(script_path) and os.path.isfile(script_path):
            return script_path

        # Relative to shared scripts dir
        candidate = os.path.join(self.shared_scripts_dir, script_path)
        if os.path.isfile(candidate):
            return candidate

        # Bare filename/job_id — look for a .py file matching the name
        for ext in ("", ".py"):
            candidate2 = os.path.join(self.shared_scripts_dir, f"{script_path}{ext}")
            if os.path.isfile(candidate2):
                return candidate2

        logger.error("Script not found: %s (searched %s)", script_path, self.shared_scripts_dir)
        return None

    def _save_logs(
        self, results_dir: str, pytest_output: str, extra_lines: List[str]
    ) -> str:
        """Write merged logs to logs.txt and return the path."""
        logs_path = os.path.join(results_dir, "logs.txt")
        with open(logs_path, "w", encoding="utf-8") as fh:
            fh.write("=== pytest output ===\n")
            fh.write(pytest_output)
            if extra_lines:
                fh.write("\n=== additional logs ===\n")
                fh.write("\n".join(extra_lines))
        return logs_path

    def _save_metrics_csv(
        self, results_dir: str, metrics: List[BrowserMetrics]
    ) -> str:
        """Write time-series metrics to metrics.csv and return the path."""
        metrics_path = os.path.join(results_dir, "metrics.csv")
        with open(metrics_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=[
                    "timestamp",
                    "memory_heap_mb",
                    "memory_total_mb",
                    "cpu_percent",
                    "network_errors_count",
                    "console_errors_count",
                    "console_warnings_count",
                ],
            )
            writer.writeheader()
            for m in metrics:
                writer.writerow(m.to_dict())
        return metrics_path

    def _error_result(
        self,
        execution_id: str,
        request: ExecutionRequest,
        started_at: datetime,
        error_message: str,
        status: ExecutionStatus = ExecutionStatus.FAILED,
    ) -> ExecutionResult:
        """Construct a failed ExecutionResult with the given error message."""
        return ExecutionResult(
            execution_id=execution_id,
            job_id=request.job_id,
            jira_ticket=request.jira_ticket,
            status=status,
            test_result=TestResult.ERROR,
            health_analysis=HealthAnalysis(
                grade=HealthGrade.CRITICAL,
                issues=[error_message],
            ),
            started_at=started_at,
            completed_at=datetime.utcnow(),
            duration_seconds=(datetime.utcnow() - started_at).total_seconds(),
            error_message=error_message,
        )
