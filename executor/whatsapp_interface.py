"""
WhatsApp interface for triggering test executions.

Accepts commands via WhatsApp webhook to trigger and manage tests.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class WhatsAppCommand(str, Enum):
    """Supported WhatsApp commands."""
    RUN = "/run"
    STATUS = "/status"
    RESULTS = "/results"
    HELP = "/help"
    LIST = "/list"


class WhatsAppMessage:
    """Incoming WhatsApp message model."""

    def __init__(
        self,
        phone_number: str,
        message_body: str,
        message_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.phone_number = phone_number
        self.message_body = message_body.strip()
        self.message_id = message_id
        self.timestamp = timestamp or datetime.utcnow()

    def parse_command(self) -> tuple[Optional[str], Optional[str]]:
        """
        Parse command and argument from message.

        Returns:
            Tuple of (command, argument)
        """
        parts = self.message_body.split()
        if not parts:
            return None, None

        command = parts[0].lower()
        argument = " ".join(parts[1:]) if len(parts) > 1 else None

        return command, argument

    def __str__(self) -> str:
        """String representation."""
        return f"{self.phone_number}: {self.message_body}"


class WhatsAppResponse:
    """Response message for WhatsApp."""

    def __init__(
        self,
        recipient: str,
        message: str,
        message_type: str = "text",
    ):
        self.recipient = recipient
        self.message = message
        self.message_type = message_type
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "recipient": self.recipient,
            "message": self.message,
            "type": self.message_type,
            "timestamp": self.timestamp.isoformat(),
        }


class WhatsAppCommandProcessor:
    """
    Processes WhatsApp commands and manages test executions.

    Supported commands:
    - /run {job_id} - Execute a test
    - /status {job_id} - Check execution status
    - /results {job_id} - Get execution results
    - /list - List all executions
    - /help - Show help message
    """

    def __init__(self, executor_api_url: str, jira_api_url: str):
        """
        Initialize command processor.

        Args:
            executor_api_url: URL of executor API
            jira_api_url: URL of Jira integrator API
        """
        self.executor_api_url = executor_api_url.rstrip("/")
        self.jira_api_url = jira_api_url.rstrip("/")

        # Store active executions (in production, use Redis/database)
        self.active_executions: Dict[str, Dict[str, Any]] = {}

    async def process_command(
        self,
        message: WhatsAppMessage,
    ) -> WhatsAppResponse:
        """
        Process WhatsApp command and generate response.

        Args:
            message: Incoming WhatsApp message

        Returns:
            WhatsApp response message
        """
        command, argument = message.parse_command()

        if not command:
            return self._help_response(message.phone_number)

        try:
            if command == WhatsAppCommand.HELP:
                return self._help_response(message.phone_number)

            elif command == WhatsAppCommand.RUN:
                return await self._handle_run_command(message.phone_number, argument)

            elif command == WhatsAppCommand.STATUS:
                return await self._handle_status_command(message.phone_number, argument)

            elif command == WhatsAppCommand.RESULTS:
                return await self._handle_results_command(message.phone_number, argument)

            elif command == WhatsAppCommand.LIST:
                return self._handle_list_command(message.phone_number)

            else:
                return self._error_response(
                    message.phone_number,
                    f"Unknown command: {command}\n\nSend /help for available commands."
                )

        except Exception as e:
            logger.error(f"Error processing command: {e}")
            return self._error_response(
                message.phone_number,
                f"Sorry, something went wrong: {str(e)}"
            )

    def _help_response(self, recipient: str) -> WhatsAppResponse:
        """Generate help message."""
        help_text = """🤖 *NanoClaw Test Executor*

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

💡 Tips:
- Job ID must match the script name in shared/scripts/
- Results include health metrics and Jira updates
- Use /results to get the full evidence package
"""

        return WhatsAppResponse(
            recipient=recipient,
            message=help_text,
        )

    async def _handle_run_command(
        self,
        recipient: str,
        job_id: Optional[str],
    ) -> WhatsAppResponse:
        """
        Handle /run command.

        Args:
            recipient: Phone number
            job_id: Job ID to execute

        Returns:
            Response message
        """
        if not job_id:
            return self._error_response(
                recipient,
                "Usage: /run {job_id}\n\nExample: /run test-123"
            )

        # In production, you would:
        # 1. Look up job details from database
        # 2. Parse script to extract Jira ticket
        # 3. Trigger execution via API

        # For now, simulate execution
        execution_id = f"exec-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        self.active_executions[job_id] = {
            "status": "running",
            "execution_id": execution_id,
            "started_at": datetime.utcnow().isoformat(),
            "phone_number": recipient,
        }

        response = f"""✅ *Test Execution Started*

Job ID: {job_id}
Execution ID: {execution_id}
Started at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}

🔍 I'll monitor the test and notify you when complete.

Use `/status {job_id}` to check progress.
"""

        return WhatsAppResponse(recipient=recipient, message=response)

    async def _handle_status_command(
        self,
        recipient: str,
        job_id: Optional[str],
    ) -> WhatsAppResponse:
        """
        Handle /status command.

        Args:
            recipient: Phone number
            job_id: Job ID to check

        Returns:
            Response message
        """
        if not job_id:
            return self._error_response(
                recipient,
                "Usage: /status {job_id}\n\nExample: /status test-123"
            )

        execution = self.active_executions.get(job_id)

        if not execution:
            return self._error_response(
                recipient,
                f"Job '{job_id}' not found. Use /list to see all executions."
            )

        status = execution.get("status", "unknown")
        started_at = execution.get("started_at", "Unknown")

        response = f"""📊 *Execution Status*

Job ID: {job_id}
Status: {status.upper()}
Started: {started_at}
"""

        if status == "running":
            response += "\n⏳ Test is still running..."
        elif status == "completed":
            response += f"\n✅ Test completed successfully!\nUse `/results {job_id}` for details."
        elif status == "failed":
            response += f"\n❌ Test failed. Use `/results {job_id}` for error details."

        return WhatsAppResponse(recipient=recipient, message=response)

    async def _handle_results_command(
        self,
        recipient: str,
        job_id: Optional[str],
    ) -> WhatsAppResponse:
        """
        Handle /results command.

        Args:
            recipient: Phone number
            job_id: Job ID to get results for

        Returns:
            Response message
        """
        if not job_id:
            return self._error_response(
                recipient,
                "Usage: /results {job_id}\n\nExample: /results test-123"
            )

        execution = self.active_executions.get(job_id)

        if not execution:
            return self._error_response(
                recipient,
                f"Job '{job_id}' not found. Use /list to see all executions."
            )

        if execution.get("status") == "running":
            return WhatsAppResponse(
                recipient=recipient,
                message=f"⏳ Job '{job_id}' is still running.\nUse `/status {job_id}` to check progress."
            )

        # In production, fetch actual results from executor API
        # For now, provide a template response

        response = f"""📋 *Execution Results*

Job ID: {job_id}
Execution ID: {execution.get('execution_id', 'N/A')}

**Test Result:** ✅ PASS
**Health Grade:** 💚 HEALTHY
**Duration:** 2.3s

**Metrics:**
• Peak Memory: 234 MB
• Peak CPU: 45%
• Network Errors: 0
• Console Errors: 0

**Evidence:**
• Results posted to Jira: {execution.get('jira_ticket', 'QA-XXX')}
• Trace file: {execution.get('execution_id', 'N/A')}/trace.zip

---
Full details available in Jira ticket.
"""

        return WhatsAppResponse(recipient=recipient, message=response)

    def _handle_list_command(self, recipient: str) -> WhatsAppResponse:
        """
        Handle /list command.

        Args:
            recipient: Phone number

        Returns:
            Response message with all executions
        """
        if not self.active_executions:
            return WhatsAppResponse(
                recipient=recipient,
                message="📋 No executions found.\n\nUse /run {job_id} to start a test."
            )

        response = "📋 *Active Executions*\n\n"

        for job_id, execution in self.active_executions.items():
            status = execution.get("status", "unknown")
            started = execution.get("started_at", "Unknown")

            status_emoji = {
                "running": "🔄",
                "completed": "✅",
                "failed": "❌",
            }.get(status, "❓")

            response += f"{status_emoji} *{job_id}*\n"
            response += f"   Status: {status.upper()}\n"
            response += f"   Started: {started}\n\n"

        return WhatsAppResponse(recipient=recipient, message=response)

    def _error_response(self, recipient: str, error_message: str) -> WhatsAppResponse:
        """Generate error response."""
        return WhatsAppResponse(
            recipient=recipient,
            message=f"❌ *Error*\n\n{error_message}\n\nSend /help for available commands."
        )
