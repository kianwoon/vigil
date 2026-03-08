"""
Jira comment formatter for NanoClaw test results.

Formats execution results into structured Jira comments.
"""

import logging
from typing import Dict, Any, List

from models import (
    ExecutionResult,
    HealthGrade,
    JiraComment,
)


logger = logging.getLogger(__name__)


class JiraCommentFormatter:
    """
    Formats execution results into Jira comments.

    Creates structured, readable comments with:
    - Status and health grade
    - Metrics table
    - Issues list
    - Evidence package descriptions
    """

    def format_execution_result(self, result: ExecutionResult) -> JiraComment:
        """
        Format execution result into Jira comment.

        Args:
            result: Execution result to format

        Returns:
            JiraComment object ready for posting
        """
        # Determine emojis and status strings
        status_emoji = "✅" if result.test_result.value == "PASS" else "❌"
        health_emoji = self._get_health_emoji(result.health_analysis.grade)
        health_label = result.health_analysis.grade.value if result.health_analysis else "UNKNOWN"

        # Create metrics table
        metrics_table = self._create_metrics_table(result)

        # Create issues list
        issues_list = self._create_issues_list(result)

        # Create evidence description
        evidence_description = self._create_evidence_description(result)

        # Create trace viewing instructions
        trace_instructions = self._create_trace_instructions()

        return JiraComment(
            ticket_id=result.jira_ticket,
            status_emoji=status_emoji,
            status=result.test_result.value,
            health_grade_emoji=health_emoji,
            health_grade=health_label,
            execution_time=f"{result.duration_seconds:.2f}s",
            timestamp=result.completed_at.isoformat() if result.completed_at else "",
            metrics_table=metrics_table,
            issues_list=issues_list,
            evidence_description=evidence_description,
            trace_view_instructions=trace_instructions,
        )

    def _get_health_emoji(self, grade: HealthGrade) -> str:
        """Get emoji for health grade."""
        emoji_map = {
            HealthGrade.HEALTHY: "💚",
            HealthGrade.WARNING: "⚠️",
            HealthGrade.CRITICAL: "🔴",
        }
        return emoji_map.get(grade, "❓")

    def _create_metrics_table(self, result: ExecutionResult) -> str:
        """
        Create markdown table for metrics.

        Args:
            result: Execution result

        Returns:
            Markdown formatted table
        """
        # Determine status icons for each metric
        memory_status = self._get_metric_status_icon(
            result.peak_memory_mb,
            threshold=500,  # 500 MB threshold
        )
        cpu_status = self._get_metric_status_icon(
            result.peak_cpu_percent,
            threshold=80,
            is_percentage=True,
        )
        network_status = self._get_metric_status_icon(
            result.total_network_errors,
            threshold=0,
            reverse=True,  # 0 is good
        )
        console_status = self._get_metric_status_icon(
            result.total_console_errors,
            threshold=0,
            reverse=True,  # 0 is good
        )

        table = f"""| Metric | Value | Status |
|--------|-------|--------|
| Peak Memory | {result.peak_memory_mb:.1f} MB | {memory_status} |
| Peak CPU | {result.peak_cpu_percent:.1f}% | {cpu_status} |
| Network Errors | {result.total_network_errors} | {network_status} |
| Console Errors | {result.total_console_errors} | {console_status} |
| Console Warnings | {result.total_console_warnings} | ℹ️ |
"""
        return table

    def _get_metric_status_icon(
        self,
        value: float,
        threshold: float,
        is_percentage: bool = False,
        reverse: bool = False,
    ) -> str:
        """
        Get status icon for metric value.

        Args:
            value: Metric value
            threshold: Threshold for warning
            is_percentage: Whether value is a percentage
            reverse: If True, lower is better

        Returns:
            Status icon
        """
        if reverse:
            if value == 0:
                return "✓ Normal"
            elif value <= threshold:
                return "⚠️ Elevated"
            else:
                return "❌ Critical"
        else:
            if value <= threshold:
                return "✓ Normal"
            elif value <= threshold * 1.2:
                return "⚠️ Elevated"
            else:
                return "❌ Critical"

    def _create_issues_list(self, result: ExecutionResult) -> str:
        """
        Create formatted list of detected issues.

        Args:
            result: Execution result

        Returns:
            Markdown formatted list
        """
        if not result.health_analysis:
            return "No health analysis available"

        issues = result.health_analysis.issues
        warnings = result.health_analysis.warnings

        if not issues and not warnings:
            return "No issues detected ✓"

        lines = []

        if issues:
            lines.append("**Critical Issues:**")
            for issue in issues:
                lines.append(f"- ❌ {issue}")

        if warnings:
            lines.append("**Warnings:**")
            for warning in warnings:
                lines.append(f"- ⚠️ {warning}")

        return "\n".join(lines)

    def _create_evidence_description(self, result: ExecutionResult) -> str:
        """
        Create description for evidence package.

        Args:
            result: Execution result

        Returns:
            Markdown formatted description
        """
        lines = [
            "**Attached Files:**",
        ]

        if result.metrics_path:
            lines.append(f"- `metrics.csv` - Time-series health data")
        if result.logs_path:
            lines.append(f"- `logs.txt` - Execution and console logs")
        if result.trace_path:
            lines.append(f"- `trace.zip` - Playwright trace viewer")
        if result.screenshot_path:
            lines.append(f"- `screenshots/` - Failure screenshots")

        return "\n".join(lines)

    def _create_trace_instructions(self) -> str:
        """
        Create instructions for viewing Playwright trace.

        Returns:
            Markdown formatted instructions
        """
        return """**View Trace:** Open the attached `trace.zip` file using one of these methods:

1. **Chrome/Edge**: Navigate to `chrome://tracing` → Click "Load" → Select trace.zip
2. **Playwright CLI**: Run `npx playwright show-trace trace.zip`
3. **VS Code**: Install Playwright extension, open trace.zip
"""
