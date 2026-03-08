"""
Adaptive Cards formatter for Teams messages.

Creates rich, interactive cards for Teams responses.
"""

import logging
from typing import Dict, Any, Optional, List


logger = logging.getLogger(__name__)


class AdaptiveCardBuilder:
    """
    Builds Adaptive Cards for Teams messages.

    Adaptive Cards provide a rich, interactive format for Teams messages
    with buttons, images, tables, and other UI elements.
    """

    def __init__(self):
        """Initialize Adaptive Card builder."""
        logger.info("AdaptiveCardBuilder initialized")

    def build_help_card(self) -> Dict[str, Any]:
        """
        Build help card with command buttons.

        Returns:
            Adaptive Card dictionary
        """
        return {
            "type": "AdaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "NanoClaw Test Executor",
                    "size": "Large",
                    "weight": "Bolder"
                },
                {
                    "type": "TextBlock",
                    "text": "Available commands:",
                    "wrap": True
                }
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "Run Test",
                    "url": "/run {job_id}"
                },
                {
                    "type": "Action.OpenUrl",
                    "title": "Check Status",
                    "url": "/status {job_id}"
                },
                {
                    "type": "Action.OpenUrl",
                    "title": "Get Results",
                    "url": "/results {job_id}"
                },
                {
                    "type": "Action.OpenUrl",
                    "title": "List All",
                    "url": "/list"
                }
            ],
            "version": "1.4"
        }

    def build_execution_started_card(
        self,
        job_id: str,
        execution_id: str,
        started_at: str,
    ) -> Dict[str, Any]:
        """
        Build card for execution started notification.

        Args:
            job_id: Job ID
            execution_id: Execution ID
            started_at: Start timestamp

        Returns:
            Adaptive Card dictionary
        """
        return {
            "type": "AdaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Test Execution Started",
                    "size": "Large",
                    "weight": "Bolder"
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {
                            "title": "Job ID:",
                            "value": job_id
                        },
                        {
                            "title": "Execution ID:",
                            "value": execution_id
                        },
                        {
                            "title": "Started at:",
                            "value": started_at
                        }
                    ]
                }
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "Check Status",
                    "url": f"/status {job_id}"
                }
            ],
            "version": "1.4"
        }

    def build_execution_status_card(
        self,
        job_id: str,
        status: str,
        started_at: str,
    ) -> Dict[str, Any]:
        """
        Build card for execution status.

        Args:
            job_id: Job ID
            status: Execution status
            started_at: Start timestamp

        Returns:
            Adaptive Card dictionary
        """
        status_color = {
            "running": "Good",
            "completed": "Good",
            "failed": "Attention",
        }.get(status.lower(), "Default")

        return {
            "type": "AdaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Execution Status",
                    "size": "Large",
                    "weight": "Bolder"
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {
                            "title": "Job ID:",
                            "value": job_id
                        },
                        {
                            "title": "Status:",
                            "value": status.upper(),
                            "color": status_color
                        },
                        {
                            "title": "Started:",
                            "value": started_at
                        }
                    ]
                }
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "Get Results",
                    "url": f"/results {job_id}"
                }
            ],
            "version": "1.4"
        }

    def build_execution_results_card(
        self,
        job_id: str,
        execution_id: str,
        test_result: str,
        health_grade: str,
        duration_seconds: float,
        metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build card for execution results.

        Args:
            job_id: Job ID
            execution_id: Execution ID
            test_result: Test result (PASS/FAIL)
            health_grade: Health grade
            duration_seconds: Execution duration
            metrics: Health metrics

        Returns:
            Adaptive Card dictionary
        """
        result_color = "Good" if test_result == "PASS" else "Attention"

        return {
            "type": "AdaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Execution Results",
                    "size": "Large",
                    "weight": "Bolder"
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {
                            "title": "Job ID:",
                            "value": job_id
                        },
                        {
                            "title": "Execution ID:",
                            "value": execution_id
                        },
                        {
                            "title": "Test Result:",
                            "value": test_result,
                            "color": result_color
                        },
                        {
                            "title": "Health Grade:",
                            "value": health_grade
                        },
                        {
                            "title": "Duration:",
                            "value": f"{duration_seconds}s"
                        }
                    ]
                },
                {
                    "type": "TextBlock",
                    "text": "Metrics",
                    "weight": "Bolder",
                    "size": "Medium"
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {
                            "title": "Peak Memory:",
                            "value": f"{metrics.get('peak_memory_mb', 0)} MB"
                        },
                        {
                            "title": "Peak CPU:",
                            "value": f"{metrics.get('peak_cpu_percent', 0)}%"
                        },
                        {
                            "title": "Network Errors:",
                            "value": str(metrics.get('total_network_errors', 0))
                        },
                        {
                            "title": "Console Errors:",
                            "value": str(metrics.get('total_console_errors', 0))
                        }
                    ]
                }
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "View in Jira",
                    "url": metrics.get('jira_url', '#')
                }
            ],
            "version": "1.4"
        }

    def build_error_card(self, error_message: str) -> Dict[str, Any]:
        """
        Build error card.

        Args:
            error_message: Error message

        Returns:
            Adaptive Card dictionary
        """
        return {
            "type": "AdaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Error",
                    "size": "Large",
                    "weight": "Bolder",
                    "color": "Attention"
                },
                {
                    "type": "TextBlock",
                    "text": error_message,
                    "wrap": True
                }
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "Help",
                    "url": "/help"
                }
            ],
            "version": "1.4"
        }

    def build_executions_list_card(self, executions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build card listing all executions.

        Args:
            executions: Dictionary of executions

        Returns:
            Adaptive Card dictionary
        """
        if not executions:
            return {
                "type": "AdaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "No executions found",
                        "size": "Medium"
                    },
                    {
                        "type": "TextBlock",
                        "text": "Use /run {job_id} to start a test.",
                        "wrap": True
                    }
                ],
                "version": "1.4"
            }

        # Build table of executions
        table_rows = []
        for job_id, execution in executions.items():
            status = execution.get("status", "unknown")
            started = execution.get("started_at", "Unknown")

            status_icon = {
                "running": "Running",
                "completed": "Completed",
                "failed": "Failed",
            }.get(status, "Unknown")

            table_rows.append([
                {
                    "type": "TextBlock",
                    "text": job_id,
                    "weight": "Bolder"
                },
                {
                    "type": "TextBlock",
                    "text": status_icon
                },
                {
                    "type": "TextBlock",
                    "text": started
                }
            ])

        return {
            "type": "AdaptiveCard",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Active Executions",
                    "size": "Large",
                    "weight": "Bolder"
                },
                {
                    "type": "Container",
                    "items": table_rows
                }
            ],
            "version": "1.4"
        }


class AdaptiveCardFormatter:
    """
    Formats responses as Adaptive Cards for Teams.
    """

    def __init__(self):
        """Initialize formatter."""
        self.builder = AdaptiveCardBuilder()

    def format_help(self) -> Dict[str, Any]:
        """Format help message as Adaptive Card."""
        return self.builder.build_help_card()

    def format_execution_started(
        self,
        job_id: str,
        execution_id: str,
        started_at: str,
    ) -> Dict[str, Any]:
        """Format execution started notification."""
        return self.builder.build_execution_started_card(job_id, execution_id, started_at)

    def format_execution_status(
        self,
        job_id: str,
        status: str,
        started_at: str,
    ) -> Dict[str, Any]:
        """Format execution status."""
        return self.builder.build_execution_status_card(job_id, status, started_at)

    def format_execution_results(
        self,
        job_id: str,
        execution_id: str,
        test_result: str,
        health_grade: str,
        duration_seconds: float,
        metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Format execution results."""
        return self.builder.build_execution_results_card(
            job_id, execution_id, test_result, health_grade, duration_seconds, metrics
        )

    def format_error(self, error_message: str) -> Dict[str, Any]:
        """Format error message."""
        return self.builder.build_error_card(error_message)

    def format_executions_list(self, executions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Format executions list."""
        return self.builder.build_executions_list_card(executions)

    def to_attachment(self, card: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Adaptive Card to attachment format.

        Args:
            card: Adaptive Card dictionary

        Returns:
            Attachment dictionary
        """
        return {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": card
        }

    def create_execution_status_card(
        self,
        job_id: str,
        status: str,
        progress: int,
    ) -> Dict[str, Any]:
        """
        Create status card with progress indicator.

        Args:
            job_id: Job identifier
            status: Current status (running, completed, failed, etc.)
            progress: Progress percentage (0-100)

        Returns:
            Adaptive Card with progress indicator
        """
        # Determine color based on status
        status_config = {
            "running": {"color": "Default", "icon": "In progress"},
            "completed": {"color": "Good", "icon": "Completed"},
            "failed": {"color": "Attention", "icon": "Failed"},
            "pending": {"color": "Default", "icon": "Pending"},
            "cancelled": {"color": "Warning", "icon": "Cancelled"},
        }

        config = status_config.get(status.lower(), status_config["pending"])

        return {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": f"Test Execution Status",
                    "size": "Large",
                    "weight": "Bolder",
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "Job ID:", "value": job_id},
                        {
                            "title": "Status:",
                            "value": f"{config['icon']}",
                        },
                    ],
                },
                {
                    "type": "TextBlock",
                    "text": f"Progress: {progress}%",
                    "weight": "Bolder",
                    "size": "Medium",
                },
                {
                    "type": "TextBlock",
                    "text": "Progress",
                    "size": "Small",
                    "color": "Default",
                    "isSubtle": True,
                },
                {
                    "type": "ProgressBar",
                    "value": progress / 100,
                },
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "Refresh Status",
                    "url": f"/status {job_id}",
                },
            ],
        }

    def create_health_grade_card(
        self,
        grade: str,
        metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create health grade card with badge.

        Args:
            grade: Health grade (HEALTHY, WARNING, CRITICAL)
            metrics: Health metrics dictionary

        Returns:
            Adaptive Card with health grade badge
        """
        # Health grade configuration with emojis
        grade_config = {
            "HEALTHY": {
                "emoji": "HEALTHY",
                "color": "Good",
                "title": "System Healthy",
            },
            "WARNING": {
                "emoji": "WARNING",
                "color": "Warning",
                "title": "Performance Warning",
            },
            "CRITICAL": {
                "emoji": "CRITICAL",
                "color": "Attention",
                "title": "Critical Issues Detected",
            },
        }

        config = grade_config.get(grade.upper(), grade_config["HEALTHY"])

        # Build metric facts
        facts = []
        for key, value in metrics.items():
            facts.append({"title": f"{key}:", "value": str(value)})

        return {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "Container",
                    "style": config["color"].lower(),
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": config["emoji"],
                            "size": "ExtraLarge",
                            "weight": "Bolder",
                            "color": config["color"],
                            "horizontalAlignment": "Center",
                        },
                        {
                            "type": "TextBlock",
                            "text": config["title"],
                            "size": "Medium",
                            "weight": "Bolder",
                            "color": config["color"],
                            "horizontalAlignment": "Center",
                        },
                    ],
                    "bleed": True,
                },
                {
                    "type": "TextBlock",
                    "text": "Health Metrics",
                    "size": "Medium",
                    "weight": "Bolder",
                },
                {
                    "type": "FactSet",
                    "facts": facts if facts else [{"title": "No metrics", "value": "available"}],
                },
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "View Details",
                    "url": metrics.get("details_url", "#"),
                },
            ],
        }

    def create_metrics_table_card(
        self,
        metrics: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Create metrics table with formatting.

        Args:
            metrics: List of metric dictionaries with 'name', 'value', 'unit' keys

        Returns:
            Adaptive Card with formatted metrics table
        """
        # Build table columns
        columns = [
            {
                "type": "Column",
                "width": "stretch",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "Metric",
                        "weight": "Bolder",
                        "size": "Small",
                    }
                ],
            },
            {
                "type": "Column",
                "width": "auto",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "Value",
                        "weight": "Bolder",
                        "size": "Small",
                        "horizontalAlignment": "Right",
                    }
                ],
            },
            {
                "type": "Column",
                "width": "auto",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "Unit",
                        "weight": "Bolder",
                        "size": "Small",
                        "horizontalAlignment": "Right",
                    }
                ],
            },
        ]

        # Build table rows
        table_rows = []
        for metric in metrics:
            name = metric.get("name", "Unknown")
            value = metric.get("value", "N/A")
            unit = metric.get("unit", "")

            # Format value with color based on thresholds
            value_color = "Default"
            if "threshold" in metric:
                if value > metric.get("threshold", {}).get("warning", float("inf")):
                    value_color = "Warning"
                if value > metric.get("threshold", {}).get("critical", float("inf")):
                    value_color = "Attention"

            table_rows.append(
                {
                    "type": "ColumnSet",
                    "columns": [
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": name,
                                    "size": "Small",
                                }
                            ],
                        },
                        {
                            "type": "Column",
                            "width": "auto",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": str(value),
                                    "size": "Small",
                                    "weight": "Bolder",
                                    "color": value_color,
                                    "horizontalAlignment": "Right",
                                }
                            ],
                        },
                        {
                            "type": "Column",
                            "width": "auto",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": unit,
                                    "size": "Small",
                                    "isSubtle": True,
                                    "horizontalAlignment": "Right",
                                }
                            ],
                        },
                    ],
                }
            )

        return {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Test Metrics",
                    "size": "Large",
                    "weight": "Bolder",
                },
                {
                    "type": "ColumnSet",
                    "columns": columns,
                },
                *table_rows,
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "Export CSV",
                    "url": "/export",
                },
            ],
        }

    def create_action_card(
        self,
        job_id: str,
        actions: List[str],
    ) -> Dict[str, Any]:
        """
        Create card with action buttons.

        Args:
            job_id: Job identifier
            actions: List of available actions (view_results, retry_test, download_trace, etc.)

        Returns:
            Adaptive Card with action buttons
        """
        # Define available actions
        action_definitions = {
            "view_results": {
                "title": "View Results",
                "url": f"/results {job_id}",
                "style": "positive",
            },
            "retry_test": {
                "title": "Retry Test",
                "url": f"/run {job_id}",
                "style": "default",
            },
            "download_trace": {
                "title": "Download Trace",
                "url": f"/download {job_id}",
                "style": "default",
            },
            "cancel": {
                "title": "Cancel",
                "url": f"/cancel {job_id}",
                "style": "destructive",
            },
            "refresh": {
                "title": "Refresh",
                "url": f"/status {job_id}",
                "style": "default",
            },
            "share": {
                "title": "Share",
                "url": f"/share {job_id}",
                "style": "default",
            },
        }

        # Build actions list
        card_actions = []
        for action in actions:
            action_def = action_definitions.get(action.lower())
            if action_def:
                card_actions.append(
                    {
                        "type": "Action.OpenUrl",
                        "title": action_def["title"],
                        "url": action_def["url"],
                    }
                )

        return {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": f"Job Actions: {job_id}",
                    "size": "Large",
                    "weight": "Bolder",
                },
                {
                    "type": "TextBlock",
                    "text": "Choose an action to perform on this job.",
                    "wrap": True,
                    "isSubtle": True,
                },
            ],
            "actions": card_actions if card_actions else [
                {
                    "type": "Action.OpenUrl",
                    "title": "No Actions Available",
                    "url": "#",
                }
            ],
        }

    def create_combined_status_card(
        self,
        job_id: str,
        status: str,
        progress: int,
        health_grade: str = "HEALTHY",
        metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create combined card with status, health grade, and actions.

        Args:
            job_id: Job identifier
            status: Current status
            progress: Progress percentage
            health_grade: Health grade (HEALTHY, WARNING, CRITICAL)
            metrics: Optional metrics dictionary

        Returns:
            Combined Adaptive Card
        """
        health_emoji = {
            "HEALTHY": "HEALTHY",
            "WARNING": "WARNING",
            "CRITICAL": "CRITICAL",
        }

        # Build metric facts if provided
        metric_facts = []
        if metrics:
            for key, value in metrics.items():
                metric_facts.append({"title": f"{key}:", "value": str(value)})

        body = [
            {
                "type": "TextBlock",
                "text": f"Job: {job_id}",
                "size": "Large",
                "weight": "Bolder",
            },
            {
                "type": "TextBlock",
                "text": health_emoji.get(health_grade.upper(), health_emoji["HEALTHY"]),
                "size": "Medium",
                "weight": "Bolder",
                "color": "Good" if health_grade == "HEALTHY" else "Attention",
            },
            {
                "type": "TextBlock",
                "text": f"Status: {status.upper()}",
                "size": "Medium",
            },
            {
                "type": "TextBlock",
                "text": f"Progress: {progress}%",
                "size": "Small",
                "isSubtle": True,
            },
            {
                "type": "ProgressBar",
                "value": progress / 100,
            },
        ]

        if metric_facts:
            body.append(
                {
                    "type": "FactSet",
                    "facts": metric_facts[:5],  # Limit to 5 metrics
                }
            )

        return {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": body,
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "View Results",
                    "url": f"/results {job_id}",
                },
                {
                    "type": "Action.OpenUrl",
                    "title": "Refresh",
                    "url": f"/status {job_id}",
                },
            ],
        }
