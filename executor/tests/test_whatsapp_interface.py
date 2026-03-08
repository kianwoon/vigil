"""
Unit tests for WhatsApp Command Processor.

Tests command parsing, routing, and response generation.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from executor.whatsapp_interface import (
    WhatsAppCommandProcessor,
    WhatsAppMessage,
    WhatsAppResponse,
    WhatsAppCommand,
)


class TestWhatsAppMessage:
    """Test suite for WhatsAppMessage."""

    def test_parse_command_with_argument(self):
        """Test parsing command with argument."""
        message = WhatsAppMessage(
            phone_number="+1234567890",
            message_body="/run test-123",
        )

        command, argument = message.parse_command()

        assert command == "/run"
        assert argument == "test-123"

    def test_parse_command_without_argument(self):
        """Test parsing command without argument."""
        message = WhatsAppMessage(
            phone_number="+1234567890",
            message_body="/help",
        )

        command, argument = message.parse_command()

        assert command == "/help"
        assert argument is None

    def test_parse_command_with_extra_spaces(self):
        """Test parsing command with extra spaces."""
        message = WhatsAppMessage(
            phone_number="+1234567890",
            message_body="/run    test-123   ",
        )

        command, argument = message.parse_command()

        assert command == "/run"
        assert argument == "test-123"

    def test_parse_command_multiword_argument(self):
        """Test parsing command with multi-word argument."""
        message = WhatsAppMessage(
            phone_number="+1234567890",
            message_body="/run test 123 description",
        )

        command, argument = message.parse_command()

        assert command == "/run"
        assert argument == "test 123 description"

    def test_parse_empty_message(self):
        """Test parsing empty message."""
        message = WhatsAppMessage(
            phone_number="+1234567890",
            message_body="   ",
        )

        command, argument = message.parse_command()

        assert command is None
        assert argument is None

    def test_string_representation(self):
        """Test message string representation."""
        message = WhatsAppMessage(
            phone_number="+1234567890",
            message_body="/run test-123",
        )

        str_repr = str(message)

        assert "+1234567890" in str_repr
        assert "/run test-123" in str_repr


class TestWhatsAppResponse:
    """Test suite for WhatsAppResponse."""

    def test_to_dict(self):
        """Test converting response to dictionary."""
        response = WhatsAppResponse(
            recipient="+1234567890",
            message="Test response",
        )

        result = response.to_dict()

        assert result["recipient"] == "+1234567890"
        assert result["message"] == "Test response"
        assert result["type"] == "text"
        assert "timestamp" in result


class TestWhatsAppCommandProcessor:
    """Test suite for WhatsAppCommandProcessor."""

    @pytest.fixture
    def processor(self):
        """Create command processor for testing."""
        return WhatsAppCommandProcessor(
            executor_api_url="http://localhost:8001",
            jira_api_url="http://localhost:8003",
        )

    @pytest.fixture
    def sample_message(self):
        """Create sample WhatsApp message."""
        return WhatsAppMessage(
            phone_number="+1234567890",
            message_body="/run test-123",
            message_id="msg-123",
            timestamp=datetime.utcnow(),
        )

    @pytest.mark.asyncio
    async def test_process_help_command(self, processor):
        """Test processing /help command."""
        message = WhatsAppMessage(
            phone_number="+1234567890",
            message_body="/help",
        )

        response = await processor.process_command(message)

        assert isinstance(response, WhatsAppResponse)
        assert response.recipient == "+1234567890"
        assert "NanoClaw Test Executor" in response.message
        assert "/run" in response.message
        assert "/status" in response.message

    @pytest.mark.asyncio
    async def test_process_run_command_success(self, processor, sample_message):
        """Test processing /run command."""
        response = await processor.process_command(sample_message)

        assert isinstance(response, WhatsAppResponse)
        assert "Test Execution Started" in response.message
        assert "test-123" in response.message
        assert sample_message.phone_number in processor.active_executions

    @pytest.mark.asyncio
    async def test_process_run_command_missing_argument(self, processor):
        """Test /run command without argument shows usage."""
        message = WhatsAppMessage(
            phone_number="+1234567890",
            message_body="/run",
        )

        response = await processor.process_command(message)

        assert "Usage:" in response.message
        assert "/run {job_id}" in response.message

    @pytest.mark.asyncio
    async def test_process_status_command_running(self, processor):
        """Test /status command for running job."""
        # First, add a running execution
        phone = "+1234567890"
        processor.active_executions["test-123"] = {
            "status": "running",
            "execution_id": "exec-abc123",
            "started_at": datetime.utcnow().isoformat(),
            "phone_number": phone,
        }

        message = WhatsAppMessage(
            phone_number=phone,
            message_body="/status test-123",
        )

        response = await processor.process_command(message)

        assert "Execution Status" in response.message
        assert "test-123" in response.message
        assert "RUNNING" in response.message

    @pytest.mark.asyncio
    async def test_process_status_command_not_found(self, processor):
        """Test /status command for non-existent job."""
        message = WhatsAppMessage(
            phone_number="+1234567890",
            message_body="/status nonexistent",
        )

        response = await processor.process_command(message)

        assert "Error" in response.message
        assert "not found" in response.message

    @pytest.mark.asyncio
    async def test_process_results_command_completed(self, processor):
        """Test /results command for completed job."""
        phone = "+1234567890"

        # Add completed execution
        processor.active_executions["test-123"] = {
            "status": "completed",
            "execution_id": "exec-abc123",
            "jira_ticket": "QA-456",
            "started_at": datetime.utcnow().isoformat(),
            "phone_number": phone,
        }

        message = WhatsAppMessage(
            phone_number=phone,
            message_body="/results test-123",
        )

        response = await processor.process_command(message)

        assert "Execution Results" in response.message
        assert "test-123" in response.message
        assert "QA-456" in response.message

    @pytest.mark.asyncio
    async def test_process_results_command_still_running(self, processor):
        """Test /results command for running job."""
        phone = "+1234567890"

        # Add running execution
        processor.active_executions["test-123"] = {
            "status": "running",
            "execution_id": "exec-abc123",
            "started_at": datetime.utcnow().isoformat(),
            "phone_number": phone,
        }

        message = WhatsAppMessage(
            phone_number=phone,
            message_body="/results test-123",
        )

        response = await processor.process_command(message)

        assert "still running" in response.message.lower()

    @pytest.mark.asyncio
    async def test_process_list_command_with_executions(self, processor):
        """Test /list command with active executions."""
        phone = "+1234567890"

        # Add multiple executions
        processor.active_executions["test-1"] = {
            "status": "completed",
            "execution_id": "exec-1",
            "started_at": datetime.utcnow().isoformat(),
            "phone_number": phone,
        }
        processor.active_executions["test-2"] = {
            "status": "running",
            "execution_id": "exec-2",
            "started_at": datetime.utcnow().isoformat(),
            "phone_number": phone,
        }

        message = WhatsAppMessage(
            phone_number=phone,
            message_body="/list",
        )

        response = await processor.process_command(message)

        assert "Active Executions" in response.message
        assert "test-1" in response.message
        assert "test-2" in response.message

    @pytest.mark.asyncio
    async def test_process_list_command_empty(self, processor):
        """Test /list command with no executions."""
        message = WhatsAppMessage(
            phone_number="+1234567890",
            message_body="/list",
        )

        response = await processor.process_command(message)

        assert "No executions found" in response.message

    @pytest.mark.asyncio
    async def test_process_unknown_command(self, processor):
        """Test processing unknown command."""
        message = WhatsAppMessage(
            phone_number="+1234567890",
            message_body="/unknown command",
        )

        response = await processor.process_command(message)

        assert "Error" in response.message
        assert "Unknown command" in response.message

    @pytest.mark.asyncio
    async def test_process_empty_message(self, processor):
        """Test processing empty message returns help."""
        message = WhatsAppMessage(
            phone_number="+1234567890",
            message_body="",
        )

        response = await processor.process_command(message)

        # Should return help message
        assert "NanoClaw" in response.message

    def test_help_response_format(self, processor):
        """Test help response contains all commands."""
        response = processor._help_response("+1234567890")

        assert "/run" in response.message
        assert "/status" in response.message
        assert "/results" in response.message
        assert "/list" in response.message
        assert "/help" in response.message
        assert "NanoClaw" in response.message

    def test_error_response_format(self, processor):
        """Test error response format."""
        response = processor._error_response(
            "+1234567890",
            "Test error message"
        )

        assert "Error" in response.message
        assert "Test error message" in response.message

    @pytest.mark.asyncio
    async def test_command_case_insensitive(self, processor):
        """Test commands are case-insensitive."""
        message = WhatsAppMessage(
            phone_number="+1234567890",
            message_body="/RUN test-123",  # Uppercase
        )

        response = await processor.process_command(message)

        # Should process successfully
        assert response.recipient == "+1234567890"
        assert "test-123" in processor.active_executions

    @pytest.mark.asyncio
    async def test_process_command_exception_handling(self, processor):
        """Test exceptions are caught and return error response."""
        # Create a message that will cause an error
        message = MagicMock()
        message.phone_number = "+1234567890"
        message.message_body = "/run test"
        message.parse_command.side_effect(Exception("Test error"))

        response = await processor.process_command(message)

        assert "Error" in response.message
        assert "something went wrong" in response.message.lower()
