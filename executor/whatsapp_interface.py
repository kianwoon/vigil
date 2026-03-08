"""
WhatsApp interface for triggering test executions.

Accepts commands via WhatsApp webhook to trigger and manage tests.
Commands are routed to the real executor API via HTTP.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

import httpx


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

    All execution-related commands are forwarded to the executor HTTP API.

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
            executor_api_url: Base URL of executor API (e.g. http://executor:8001)
            jira_api_url: Base URL of Jira integrator API
        """
        self.executor_api_url = executor_api_url.rstrip("/")
        self.jira_api_url = jira_api_url.rstrip("/")

        # Mirror of executor's active_executions for mapping phone → job_id
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
                return await self._handle_list_command(message.phone_number)

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
        Handle /run command — calls the executor API to start test execution.

        Args:
            recipient: Sender phone number
            job_id: Job ID (also used as script_path lookup)

        Returns:
            Response message
        """
        if not job_id:
            return self._error_response(
                recipient,
                "Usage: /run {job_id}\n\nExample: /run test-123"
            )

        payload = {
            "job_id": job_id,
            "jira_ticket": job_id,        # Caller can pass a full ticket ID as job_id
            "script_path": job_id,        # Runner will search shared/scripts/ by name
            "timeout_seconds": 300,
            "browser_headless": True,
            "trace_enabled": True,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(
                    f"{self.executor_api_url}/api/v1/execute",
                    json=payload,
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = exc.response.json().get("detail", str(exc))
                return self._error_response(recipient, f"Executor rejected request: {detail}")
            except httpx.RequestError as exc:
                return self._error_response(recipient, f"Could not reach executor: {exc}")

        data = resp.json()
        self.active_executions[job_id] = {
            "phone_number": recipient,
            "started_at": datetime.utcnow().isoformat(),
        }

        response = f"""✅ *Test Execution Started*

Job ID: {job_id}
Status: {data.get('status', 'accepted').upper()}
Jira Ticket: {data.get('jira_ticket', job_id)}
Started at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

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
        Handle /status command — queries the executor API for live status.

        Args:
            recipient: Sender phone number
            job_id: Job ID to check

        Returns:
            Response message
        """
        if not job_id:
            return self._error_response(
                recipient,
                "Usage: /status {job_id}\n\nExample: /status test-123"
            )

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    f"{self.executor_api_url}/api/v1/status/{job_id}"
                )
                if resp.status_code == 404:
                    return self._error_response(
                        recipient,
                        f"Job '{job_id}' not found. Use /list to see all executions."
                    )
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = exc.response.json().get("detail", str(exc))
                return self._error_response(recipient, f"Executor error: {detail}")
            except httpx.RequestError as exc:
                return self._error_response(recipient, f"Could not reach executor: {exc}")

        data = resp.json()
        status = data.get("status", "unknown").upper()
        duration = data.get("duration_seconds", 0)

        STATUS_EMOJI = {
            "RUNNING": "⏳",
            "COMPLETED": "✅",
            "FAILED": "❌",
            "TIMEOUT": "⏰",
        }
        emoji = STATUS_EMOJI.get(status, "❓")

        response = f"""📊 *Execution Status*

Job ID: {job_id}
Status: {emoji} {status}
Duration: {duration:.1f}s
"""

        if status == "RUNNING":
            response += "\n⏳ Test is still running..."
        elif status == "COMPLETED":
            test_result = data.get("test_result", "UNKNOWN")
            health_grade = data.get("health_grade", "UNKNOWN")
            response += f"\n✅ Complete — Result: {test_result} | Health: {health_grade}"
            response += f"\nUse `/results {job_id}` for details."
        elif status in ("FAILED", "TIMEOUT"):
            error = data.get("error", "Unknown error")
            response += f"\n❌ {status}: {error}"

        return WhatsAppResponse(recipient=recipient, message=response)

    async def _handle_results_command(
        self,
        recipient: str,
        job_id: Optional[str],
    ) -> WhatsAppResponse:
        """
        Handle /results command — fetches the full result from the executor API.

        Args:
            recipient: Sender phone number
            job_id: Job ID to get results for

        Returns:
            Response message
        """
        if not job_id:
            return self._error_response(
                recipient,
                "Usage: /results {job_id}\n\nExample: /results test-123"
            )

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    f"{self.executor_api_url}/api/v1/result/{job_id}"
                )
                if resp.status_code == 404:
                    return self._error_response(
                        recipient,
                        f"Job '{job_id}' not found. Use /list to see all executions."
                    )
                if resp.status_code == 400:
                    return WhatsAppResponse(
                        recipient=recipient,
                        message=f"⏳ Job '{job_id}' is still running.\nUse `/status {job_id}` to check progress."
                    )
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = exc.response.json().get("detail", str(exc))
                return self._error_response(recipient, f"Executor error: {detail}")
            except httpx.RequestError as exc:
                return self._error_response(recipient, f"Could not reach executor: {exc}")

        data = resp.json()
        test_result = data.get("test_result", "UNKNOWN")
        health_grade = data.get("health_grade", "UNKNOWN")
        duration = data.get("duration_seconds", 0)
        metrics = data.get("metrics", {})
        evidence = data.get("evidence_package", {})
        jira_ticket = data.get("jira_ticket", "N/A")

        RESULT_EMOJI = {"PASS": "✅", "FAIL": "❌", "ERROR": "💥", "SKIPPED": "⏭️"}
        GRADE_EMOJI = {"HEALTHY": "💚", "WARNING": "⚠️", "CRITICAL": "🔴"}

        response = f"""📋 *Execution Results*

Job ID: {job_id}
Execution ID: {data.get('execution_id', 'N/A')}

*Test Result:* {RESULT_EMOJI.get(test_result, '❓')} {test_result}
*Health Grade:* {GRADE_EMOJI.get(health_grade, '❓')} {health_grade}
*Duration:* {duration:.1f}s

*Metrics:*
• Peak Memory: {metrics.get('peak_memory_mb', 0):.0f} MB
• Peak CPU: {metrics.get('peak_cpu_percent', 0):.0f}%
• Network Errors: {metrics.get('network_errors', 0)}
• Console Errors: {metrics.get('console_errors', 0)}

*Evidence:*
• Jira Ticket: {jira_ticket}
• Trace: {evidence.get('trace', 'N/A')}
• Logs: {evidence.get('logs', 'N/A')}

---
Full details available in Jira ticket.
"""

        return WhatsAppResponse(recipient=recipient, message=response)

    async def _handle_list_command(self, recipient: str) -> WhatsAppResponse:
        """
        Handle /list command — queries executor API for all active executions.

        Args:
            recipient: Sender phone number

        Returns:
            Response message with all known executions
        """
        # Executor doesn't expose a /list endpoint yet; fall back to local cache
        if not self.active_executions:
            return WhatsAppResponse(
                recipient=recipient,
                message="📋 No executions found.\n\nUse /run {job_id} to start a test."
            )

        response = "📋 *Known Executions*\n\n"
        for job_id in self.active_executions:
            response += f"• {job_id} — use `/status {job_id}` for live status\n"

        return WhatsAppResponse(recipient=recipient, message=response)

    def _error_response(self, recipient: str, error_message: str) -> WhatsAppResponse:
        """Generate error response."""
        return WhatsAppResponse(
            recipient=recipient,
            message=f"❌ *Error*\n\n{error_message}\n\nSend /help for available commands."
        )
