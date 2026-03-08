"""
Evidence packager for NanoClaw test executions.

Generates and organizes evidence packages for Jira attachments.
"""

import csv
import os
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from models import (
    ExecutionResult,
    EvidencePackage,
    BrowserMetrics,
)


logger = logging.getLogger(__name__)


class EvidencePackager:
    """
    Packages execution evidence for Jira attachment.

    Creates:
    - metrics.csv: Time-series health metrics
    - logs.txt: Merged execution and console logs
    - health_report.json: Detailed health analysis
    - Screenshots directory (if any failures)
    """

    def __init__(self, output_dir: str):
        """
        Initialize evidence packager.

        Args:
            output_dir: Base directory for evidence packages
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_package(
        self,
        result: ExecutionResult,
        metrics_buffer: List[BrowserMetrics],
        execution_log: str,
        console_log: str,
    ) -> EvidencePackage:
        """
        Create complete evidence package for execution.

        Args:
            result: Execution result
            metrics_buffer: Collected browser metrics
            execution_log: Terminal output from test execution
            console_log: Browser console output

        Returns:
            EvidencePackage with file paths
        """
        # Create execution-specific directory
        exec_dir = self.output_dir / result.execution_id
        exec_dir.mkdir(exist_ok=True)

        logger.info(f"Creating evidence package in {exec_dir}")

        # Generate metrics CSV
        metrics_csv_path = exec_dir / "metrics.csv"
        self._generate_metrics_csv(metrics_csv_path, metrics_buffer)

        # Generate logs
        logs_txt_path = exec_dir / "logs.txt"
        self._generate_logs(logs_txt_path, execution_log, console_log)

        # Generate health report
        health_report_path = exec_dir / "health_report.json"
        self._generate_health_report(health_report_path, result)

        # Copy trace file if exists
        trace_zip_path = None
        if result.trace_path and os.path.exists(result.trace_path):
            trace_zip_path = exec_dir / "trace.zip"
            import shutil
            shutil.copy2(result.trace_path, trace_zip_path)

        # Copy screenshots if any
        screenshot_dir = None
        if result.screenshot_path and os.path.exists(result.screenshot_path):
            screenshot_dir = exec_dir / "screenshots"
            shutil.copytree(result.screenshot_path, screenshot_dir)

        # Create evidence package
        package = EvidencePackage(
            execution_id=result.execution_id,
            job_id=result.job_id,
            jira_ticket=result.jira_ticket,
            test_name=result.test_result.value,  # Use test name if available
            metrics_csv_path=str(metrics_csv_path),
            logs_txt_path=str(logs_txt_path),
            trace_zip_path=str(trace_zip_path) if trace_zip_path else None,
            health_report_json_path=str(health_report_path),
            screenshot_dir=str(screenshot_dir) if screenshot_dir else None,
        )

        logger.info(f"Evidence package created: {package}")
        return package

    def _generate_metrics_csv(
        self,
        output_path: Path,
        metrics: List[BrowserMetrics],
    ) -> None:
        """
        Generate CSV file with time-series metrics.

        Args:
            output_path: Output CSV file path
            metrics: List of browser metrics
        """
        with open(output_path, "w", newline="") as csvfile:
            fieldnames = [
                "timestamp",
                "memory_heap_mb",
                "memory_total_mb",
                "cpu_percent",
                "network_errors_count",
                "console_errors_count",
                "console_warnings_count",
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for metric in metrics:
                writer.writerow({
                    "timestamp": metric.timestamp.isoformat(),
                    "memory_heap_mb": f"{metric.memory_heap_mb:.2f}",
                    "memory_total_mb": f"{metric.memory_total_mb:.2f}",
                    "cpu_percent": f"{metric.cpu_percent:.2f}",
                    "network_errors_count": len(metric.network_errors),
                    "console_errors_count": len(metric.console_errors),
                    "console_warnings_count": len(metric.console_warnings),
                })

        logger.debug(f"Metrics CSV created: {output_path}")

    def _generate_logs(
        self,
        output_path: Path,
        execution_log: str,
        console_log: str,
    ) -> None:
        """
        Generate merged logs file.

        Args:
            output_path: Output log file path
            execution_log: Terminal output
            console_log: Browser console output
        """
        with open(output_path, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("NanoClaw Execution Log\n")
            f.write(f"Generated: {datetime.utcnow().isoformat()}\n")
            f.write("=" * 80 + "\n\n")

            f.write("-" * 80 + "\n")
            f.write("TERMINAL OUTPUT\n")
            f.write("-" * 80 + "\n")
            f.write(execution_log)
            f.write("\n\n")

            f.write("-" * 80 + "\n")
            f.write("BROWSER CONSOLE\n")
            f.write("-" * 80 + "\n")
            f.write(console_log)

        logger.debug(f"Logs file created: {output_path}")

    def _generate_health_report(
        self,
        output_path: Path,
        result: ExecutionResult,
    ) -> None:
        """
        Generate detailed health analysis JSON report.

        Args:
            output_path: Output JSON file path
            result: Execution result
        """
        report = {
            "execution_id": result.execution_id,
            "job_id": result.job_id,
            "jira_ticket": result.jira_ticket,
            "timestamp": datetime.utcnow().isoformat(),
            "test_result": result.test_result.value,
            "health_grade": result.health_analysis.grade.value if result.health_analysis else None,
            "duration_seconds": result.duration_seconds,
            "metrics": {
                "peak_memory_mb": result.peak_memory_mb,
                "peak_cpu_percent": result.peak_cpu_percent,
                "total_network_errors": result.total_network_errors,
                "total_console_errors": result.total_console_errors,
                "total_console_warnings": result.total_console_warnings,
            },
            "health_analysis": {
                "issues": result.health_analysis.issues if result.health_analysis else [],
                "warnings": result.health_analysis.warnings if result.health_analysis else [],
                "metrics_summary": result.health_analysis.metrics_summary if result.health_analysis else {},
            },
            "evidence_files": {
                "trace": result.trace_path,
                "logs": result.logs_path,
                "screenshot": result.screenshot_path,
            },
        }

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.debug(f"Health report created: {output_path}")
