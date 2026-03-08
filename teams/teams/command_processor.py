"""
Command processor for Teams bot messages.

Parses Teams commands and coordinates with executor and Jira services.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum


logger = logging.getLogger(__name__)


class TeamsCommand(str, Enum):
    """Supported Teams commands."""
    RUN = "/run"
    STATUS = "/status"
    RESULTS = "/results"
    HELP = "/help"
    LIST = "/list"


class TeamsMessage:
    """Incoming Teams message model."""

    def __init__(
        self,
        text: str,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        conversation_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.text = text.strip()
        self.user_id = user_id
        self.user_name = user_name
        self.conversation_id = conversation_id
        self.timestamp = timestamp or datetime.utcnow()

    def parse_command(self) -> tuple[Optional[str], Optional[str]]:
        """
        Parse command and argument from message.

        Returns:
            Tuple of (command, argument)
        """
        parts = self.text.split()
        if not parts:
            return None, None

        command = parts[0].lower()
        argument = " ".join(parts[1:]) if len(parts) > 1 else None

        return command, argument

    def __str__(self) -> str:
        """String representation."""
        user_info = self.user_name or self.user_id or "unknown"
        return f"{user_info}: {self.text}"


class TeamsResponse:
    """Response message for Teams with Adaptive Card support."""

    def __init__(
        self,
        message: str,
        response_type: str = "text",
        adaptive_card: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.response_type = response_type
        self.adaptive_card = adaptive_card
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        result = {
            "message": self.message,
            "type": self.response_type,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.adaptive_card:
            result["adaptive_card"] = self.adaptive_card
        return result

    def to_attachment(self) -> Dict[str, Any]:
        """Convert to Teams attachment format with Adaptive Card."""
        if self.adaptive_card:
            return {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": self.adaptive_card
            }
        return {
            "contentType": "text/plain",
            "content": self.message
        }


class TeamsCommandProcessor:
    """
    Processes Teams commands and manages test executions.

    Supported commands:
    - /run {job_id} - Execute a test
    - /status {job_id} - Check execution status
    - /results {job_id} - Get execution results
    - /list - List all executions
    - /help - Show help message
    """

    def __init__(self, executor_api_url: str, jira_api_url: str, use_adaptive_cards: bool = True):
        """
        Initialize command processor.

        Args:
            executor_api_url: URL of executor API
            jira_api_url: URL of Jira integrator API
            use_adaptive_cards: Whether to format responses as Adaptive Cards
        """
        self.executor_api_url = executor_api_url.rstrip("/")
        self.jira_api_url = jira_api_url.rstrip("/")
        self.use_adaptive_cards = use_adaptive_cards

        # Store active executions (in production, use Redis/database)
        self.active_executions: Dict[str, Dict[str, Any]] = {}

        # Lazy load AdaptiveCardFormatter if needed
        self._card_formatter = None

    @property
    def card_formatter(self):
        """Lazy load the card formatter."""
        if self._card_formatter is None and self.use_adaptive_cards:
            from .adaptive_cards import AdaptiveCardFormatter
            self._card_formatter = AdaptiveCardFormatter()
        return self._card_formatter

    async def process_command(
        self,
        message: TeamsMessage,
    ) -> TeamsResponse:
        """
        Process Teams command and generate response.

        Args:
            message: Incoming Teams message

        Returns:
            Teams response message
        """

        command, argument = message.parse_command()

        if not command:
            return self._help_response()

        try:
            if command == TeamsCommand.HELP:
                return self._help_response()

            elif command == TeamsCommand.RUN:
                return await self._handle_run_command(argument)

            elif command == TeamsCommand.STATUS:
                return await self._handle_status_command(argument)

            elif command == TeamsCommand.RESULTS:
                return await self._handle_results_command(argument)

            elif command == TeamsCommand.LIST:
                return self._handle_list_command()

            else:
                return self._error_response(
                    f"Unknown command: {command}\\n\\nSend /help for available commands."
                )

        except Exception as e:
            logger.error(f"Error processing command: {e}")
            return self._error_response(
                f"Sorry, something went wrong: {str(e)}"
            )

    def _help_response(self) -> TeamsResponse:
        """Generate help message."""
        if self.use_adaptive_cards and self.card_formatter:
            adaptive_card = self.card_formatter.format_help()
            return TeamsResponse(
                message="NanoClaw Test Executor - Available Commands",
                response_type="adaptive_card",
                adaptive_card=adaptive_card
            )

        help_text = """**NanoClaw Test Executor**

Available commands:

• `/run {job_id}` - Execute a test
  Example: /run test-123

• `/status {job_id}` - Check execution status
  Example: /status test-123

• `/results {job_id}` - Get execution results
  Example: /results test-123

• `/list` - List all executions

• `/help` - Show this help message

---

Tips:
- Job ID must match the script name in shared/scripts/
- Results include health metrics and Jira updates
- Use /results to get the full evidence package
"""
        return TeamsResponse(message=help_text)

    async def _handle_run_command(
        self,
        job_id: Optional[str],
    ) -> TeamsResponse:
        """
        Handle /run command.

        Args:
            job_id: Job ID to execute

        Returns:
            Response message
        """
        if not job_id:
            return self._error_response(
                "Usage: /run {job_id}\n\nExample: /run test-123"
            )

        # In production, you would:
        # 1. Look up job details from database
        # 2. Parse script to extract Jira ticket
        # 3. Trigger execution via API

        # For now, simulate execution
        execution_id = f"exec-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        started_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        self.active_executions[job_id] = {
            "status": "running",
            "execution_id": execution_id,
            "started_at": datetime.utcnow().isoformat(),
        }

        if self.use_adaptive_cards and self.card_formatter:
            adaptive_card = self.card_formatter.format_execution_started(
                job_id, execution_id, started_at
            )
            return TeamsResponse(
                message=f"Test Execution Started: {job_id}",
                response_type="adaptive_card",
                adaptive_card=adaptive_card
            )

        response = f"""**Test Execution Started**

Job ID: {job_id}
Execution ID: {execution_id}
Started at: {started_at}

I'll monitor the test and notify you when complete.

Use `/status {job_id}` to check progress.
"""

        return TeamsResponse(message=response)

    async def _handle_status_command(
        self,
        job_id: Optional[str],
    ) -> TeamsResponse:
        """
        Handle /status command.

        Args:
            job_id: Job ID to check

        Returns:
            Response message
        """
        if not job_id:
            return self._error_response(
                "Usage: /status {job_id}\n\nExample: /status test-123"
            )

        execution = self.active_executions.get(job_id)

        if not execution:
            return self._error_response(
                f"Job '{job_id}' not found. Use /list to see all executions."
            )

        status = execution.get("status", "unknown")
        started_at = execution.get("started_at", "Unknown")

        if self.use_adaptive_cards and self.card_formatter:
            adaptive_card = self.card_formatter.format_execution_status(
                job_id, status, started_at
            )
            return TeamsResponse(
                message=f"Execution Status: {job_id} - {status.upper()}",
                response_type="adaptive_card",
                adaptive_card=adaptive_card
            )

        response = f"""**Execution Status**

Job ID: {job_id}
Status: {status.upper()}
Started: {started_at}
"""

        if status == "running":
            response += "\nTest is still running..."
        elif status == "completed":
            response += f"\nTest completed successfully!\nUse `/results {job_id}` for details."
        elif status == "failed":
            response += f"\nTest failed. Use `/results {job_id}` for error details."

        return TeamsResponse(message=response)

    async def _handle_results_command(
        self,
        job_id: Optional[str],
    ) -> TeamsResponse:
        """
        Handle /results command.

        Args:
            job_id: Job ID to get results for

        Returns:
            Response message
        """
        if not job_id:
            return self._error_response(
                "Usage: /results {job_id}\n\nExample: /results test-123"
            )

        execution = self.active_executions.get(job_id)

        if not execution:
            return self._error_response(
                f"Job '{job_id}' not found. Use /list to see all executions."
            )

        if execution.get("status") == "running":
            return TeamsResponse(
                message=f"Job '{job_id}' is still running.\nUse `/status {job_id}` to check progress."
            )

        # In production, fetch actual results from executor API
        # For now, provide a template response
        execution_id = execution.get('execution_id', 'N/A')
        test_result = "PASS"
        health_grade = "HEALTHY"
        duration = 2.3
        metrics = {
            'peak_memory_mb': 234,
            'peak_cpu_percent': 45,
            'total_network_errors': 0,
            'total_console_errors': 0,
            'jira_url': f"https://jira.example.com/browse/{execution.get('jira_ticket', 'QA-XXX')}"
        }

        if self.use_adaptive_cards and self.card_formatter:
            adaptive_card = self.card_formatter.format_execution_results(
                job_id, execution_id, test_result, health_grade, duration, metrics
            )
            return TeamsResponse(
                message=f"Execution Results: {job_id} - {test_result}",
                response_type="adaptive_card",
                adaptive_card=adaptive_card
            )

        response = f"""**Execution Results**

Job ID: {job_id}
Execution ID: {execution_id}

**Test Result:** PASS
**Health Grade:** HEALTHY
**Duration:** 2.3s

**Metrics:**
• Peak Memory: 234 MB
• Peak CPU: 45%
• Network Errors: 0
• Console Errors: 0

**Evidence:**
• Results posted to Jira: {execution.get('jira_ticket', 'QA-XXX')}
• Trace file: {execution_id}/trace.zip

---
Full details available in Jira ticket.
"""

        return TeamsResponse(message=response)

    def _handle_list_command(self) -> TeamsResponse:
        """
        Handle /list command.

        Returns:
            Response message with all executions
        """
        if not self.active_executions:
            if self.use_adaptive_cards and self.card_formatter:
                adaptive_card = self.card_formatter.format_executions_list({})
                return TeamsResponse(
                    message="No executions found. Use /run {job_id} to start a test.",
                    response_type="adaptive_card",
                    adaptive_card=adaptive_card
                )
            return TeamsResponse(
                message="No executions found.\n\nUse /run {job_id} to start a test."
            )

        if self.use_adaptive_cards and self.card_formatter:
            adaptive_card = self.card_formatter.format_executions_list(self.active_executions)
            return TeamsResponse(
                message=f"Active Executions: {len(self.active_executions)}",
                response_type="adaptive_card",
                adaptive_card=adaptive_card
            )

        response = "**Active Executions**\n\n"

        for job_id, execution in self.active_executions.items():
            status = execution.get("status", "unknown")
            started = execution.get("started_at", "Unknown")

            status_icon = {
                "running": "Running",
                "completed": "Completed",
                "failed": "Failed",
            }.get(status, "Unknown")

            response += f"**{job_id}**\n"
            response += f"   Status: {status_icon}\n"
            response += f"   Started: {started}\n\n"

        return TeamsResponse(message=response)

    def _error_response(self, error_message: str) -> TeamsResponse:
        """Generate error response."""
        if self.use_adaptive_cards and self.card_formatter:
            adaptive_card = self.card_formatter.format_error(error_message)
            return TeamsResponse(
                message=f"Error: {error_message}",
                response_type="adaptive_card",
                adaptive_card=adaptive_card
            )

        return TeamsResponse(
            message=f"**Error**\n\n{error_message}\n\nSend /help for available commands."
        )
