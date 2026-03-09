"""
Unit tests for Teams Command Processor.

Tests command parsing, routing, and response generation.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from teams.teams.command_processor import (
    TeamsCommandProcessor,
    TeamsMessage,
    TeamsResponse,
    TeamsCommand,
)


class TestTeamsMessage:
    """Test suite for TeamsMessage."""

    def test_parse_command_with_argument(self):
        """Test parsing command with argument."""
        message = TeamsMessage(
            text="/run test-123",
            conversation_id="conv123",
            user_id="user456",
        )

        command, argument = message.parse_command()

        assert command == "/run"
        assert argument == "test-123"

    def test_parse_command_without_argument(self):
        """Test parsing command without argument."""
        message = TeamsMessage(
            text="/help",
            conversation_id="conv123",
            user_id="user456",
        )

        command, argument = message.parse_command()

        assert command == "/help"
        assert argument is None

    def test_parse_command_with_extra_spaces(self):
        """Test parsing command with extra spaces."""
        message = TeamsMessage(
            text="/run    test-123   ",
            conversation_id="conv123",
            user_id="user456",
        )

        command, argument = message.parse_command()

        assert command == "/run"
        assert argument == "test-123"

    def test_parse_command_multiword_argument(self):
        """Test parsing command with multi-word argument."""
        message = TeamsMessage(
            text="/run test 123 description",
            conversation_id="conv123",
            user_id="user456",
        )

        command, argument = message.parse_command()

        assert command == "/run"
        assert argument == "test 123 description"

    def test_parse_empty_message(self):
        """Test parsing empty message."""
        message = TeamsMessage(
            text="   ",
            conversation_id="conv123",
            user_id="user456",
        )

        command, argument = message.parse_command()

        assert command is None
        assert argument is None

    def test_parse_command_case_insensitive(self):
        """Test parsing converts command to lowercase."""
        message = TeamsMessage(
            text="/RUN Test-123",
            conversation_id="conv123",
            user_id="user456",
        )

        command, argument = message.parse_command()

        assert command == "/run"
        assert argument == "Test-123"

    def test_string_representation_with_user_name(self):
        """Test message string representation with user name."""
        message = TeamsMessage(
            text="/run test-123",
            user_id="user456",
            user_name="John Doe",
            conversation_id="conv123",
        )

        str_repr = str(message)

        assert "John Doe" in str_repr
        assert "/run test-123" in str_repr

    def test_string_representation_without_user_name(self):
        """Test message string representation without user name."""
        message = TeamsMessage(
            text="/run test-123",
            user_id="user456",
            conversation_id="conv123",
        )

        str_repr = str(message)

        assert "user456" in str_repr
        assert "/run test-123" in str_repr

    def test_timestamp_defaults_to_now(self):
        """Test timestamp defaults to current time."""
        before = datetime.utcnow()
        message = TeamsMessage(text="/run test-123")
        after = datetime.utcnow()

        assert message.timestamp is not None
        assert before <= message.timestamp <= after

    def test_text_is_stripped(self):
        """Test text is stripped on initialization."""
        message = TeamsMessage(
            text="  /run test-123  ",
            conversation_id="conv123",
        )

        assert message.text == "/run test-123"


class TestTeamsResponse:
    """Test suite for TeamsResponse."""

    def test_to_dict_text_response(self):
        """Test converting text response to dictionary."""
        response = TeamsResponse(
            message="Test response",
            response_type="text",
        )

        result = response.to_dict()

        assert result["message"] == "Test response"
        assert result["type"] == "text"
        assert "timestamp" in result

    def test_to_dict_with_adaptive_card(self):
        """Test converting response with adaptive card to dictionary."""
        adaptive_card = {"type": "AdaptiveCard", "body": []}
        response = TeamsResponse(
            message="Test response",
            response_type="adaptive_card",
            adaptive_card=adaptive_card,
        )

        result = response.to_dict()

        assert result["message"] == "Test response"
        assert result["type"] == "adaptive_card"
        assert result["adaptive_card"] == adaptive_card
        assert "timestamp" in result

    def test_to_attachment_text(self):
        """Test converting text response to Teams attachment format."""
        response = TeamsResponse(
            message="Test response",
            response_type="text",
        )

        attachment = response.to_attachment()

        assert attachment["contentType"] == "text/plain"
        assert attachment["content"] == "Test response"

    def test_to_attachment_adaptive_card(self):
        """Test converting adaptive card response to Teams attachment format."""
        adaptive_card = {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [{"type": "TextBlock", "text": "Hello"}]
        }
        response = TeamsResponse(
            message="Test response",
            response_type="adaptive_card",
            adaptive_card=adaptive_card,
        )

        attachment = response.to_attachment()

        assert attachment["contentType"] == "application/vnd.microsoft.card.adaptive"
        assert attachment["content"] == adaptive_card

    def test_timestamp_set_on_creation(self):
        """Test timestamp is set on response creation."""
        before = datetime.utcnow()
        response = TeamsResponse(message="Test")
        after = datetime.utcnow()

        assert before <= response.timestamp <= after


class TestTeamsCommandProcessor:
    """Test suite for TeamsCommandProcessor."""

    @pytest.fixture
    def processor(self):
        """Create command processor for testing."""
        return TeamsCommandProcessor(
            executor_api_url="http://localhost:8001",
            jira_api_url="http://localhost:8003",
            use_adaptive_cards=False,  # Disable for simpler testing
        )

    @pytest.fixture
    def processor_with_cards(self):
        """Create command processor with adaptive cards enabled."""
        return TeamsCommandProcessor(
            executor_api_url="http://localhost:8001",
            jira_api_url="http://localhost:8003",
            use_adaptive_cards=True,
        )

    @pytest.fixture
    def sample_message(self):
        """Create sample Teams message."""
        return TeamsMessage(
            text="/run test-123",
            user_id="user456",
            user_name="Test User",
            conversation_id="conv123",
            timestamp=datetime.utcnow(),
        )

    @pytest.mark.asyncio
    async def test_process_help_command(self, processor):
        """Test processing /help command."""
        message = TeamsMessage(
            text="/help",
            conversation_id="conv123",
            user_id="user456",
        )

        response = await processor.process_command(message)

        assert isinstance(response, TeamsResponse)
        assert "Vigil Test Executor" in response.message
        assert "/run" in response.message
        assert "/status" in response.message
        assert "/results" in response.message
        assert "/list" in response.message
        assert "/help" in response.message

    @pytest.mark.asyncio
    async def test_process_run_command_success(self, processor, sample_message):
        """Test processing /run command."""
        response = await processor.process_command(sample_message)

        assert isinstance(response, TeamsResponse)
        assert "Test Execution Started" in response.message
        assert "test-123" in response.message
        assert "test-123" in processor.active_executions
        assert processor.active_executions["test-123"]["status"] == "running"

    @pytest.mark.asyncio
    async def test_process_run_command_missing_argument(self, processor):
        """Test /run command without argument shows usage."""
        message = TeamsMessage(
            text="/run",
            conversation_id="conv123",
            user_id="user456",
        )

        response = await processor.process_command(message)

        assert "Usage:" in response.message
        assert "/run {job_id}" in response.message
        assert "test-123" not in processor.active_executions

    @pytest.mark.asyncio
    async def test_process_status_command_running(self, processor):
        """Test /status command for running job."""
        # Add a running execution
        processor.active_executions["test-123"] = {
            "status": "running",
            "execution_id": "exec-abc123",
            "started_at": datetime.utcnow().isoformat(),
        }

        message = TeamsMessage(
            text="/status test-123",
            conversation_id="conv123",
            user_id="user456",
        )

        response = await processor.process_command(message)

        assert "Execution Status" in response.message
        assert "test-123" in response.message
        assert "RUNNING" in response.message

    @pytest.mark.asyncio
    async def test_process_status_command_completed(self, processor):
        """Test /status command for completed job."""
        processor.active_executions["test-123"] = {
            "status": "completed",
            "execution_id": "exec-abc123",
            "jira_ticket": "QA-456",
            "started_at": datetime.utcnow().isoformat(),
        }

        message = TeamsMessage(
            text="/status test-123",
            conversation_id="conv123",
            user_id="user456",
        )

        response = await processor.process_command(message)

        assert "Execution Status" in response.message
        assert "test-123" in response.message
        assert "COMPLETED" in response.message
        assert "/results" in response.message

    @pytest.mark.asyncio
    async def test_process_status_command_failed(self, processor):
        """Test /status command for failed job."""
        processor.active_executions["test-123"] = {
            "status": "failed",
            "execution_id": "exec-abc123",
            "started_at": datetime.utcnow().isoformat(),
        }

        message = TeamsMessage(
            text="/status test-123",
            conversation_id="conv123",
            user_id="user456",
        )

        response = await processor.process_command(message)

        assert "FAILED" in response.message
        assert "/results" in response.message

    @pytest.mark.asyncio
    async def test_process_status_command_missing_argument(self, processor):
        """Test /status command without argument shows usage."""
        message = TeamsMessage(
            text="/status",
            conversation_id="conv123",
            user_id="user456",
        )

        response = await processor.process_command(message)

        assert "Usage:" in response.message
        assert "/status {job_id}" in response.message

    @pytest.mark.asyncio
    async def test_process_status_command_not_found(self, processor):
        """Test /status command for non-existent job."""
        message = TeamsMessage(
            text="/status nonexistent",
            conversation_id="conv123",
            user_id="user456",
        )

        response = await processor.process_command(message)

        assert "Error" in response.message
        assert "not found" in response.message

    @pytest.mark.asyncio
    async def test_process_results_command_completed(self, processor):
        """Test /results command for completed job."""
        processor.active_executions["test-123"] = {
            "status": "completed",
            "execution_id": "exec-abc123",
            "jira_ticket": "QA-456",
            "started_at": datetime.utcnow().isoformat(),
        }

        message = TeamsMessage(
            text="/results test-123",
            conversation_id="conv123",
            user_id="user456",
        )

        response = await processor.process_command(message)

        assert "Execution Results" in response.message
        assert "test-123" in response.message
        assert "QA-456" in response.message
        assert "PASS" in response.message
        assert "HEALTHY" in response.message

    @pytest.mark.asyncio
    async def test_process_results_command_still_running(self, processor):
        """Test /results command for running job."""
        processor.active_executions["test-123"] = {
            "status": "running",
            "execution_id": "exec-abc123",
            "started_at": datetime.utcnow().isoformat(),
        }

        message = TeamsMessage(
            text="/results test-123",
            conversation_id="conv123",
            user_id="user456",
        )

        response = await processor.process_command(message)

        assert "still running" in response.message.lower()

    @pytest.mark.asyncio
    async def test_process_results_command_missing_argument(self, processor):
        """Test /results command without argument shows usage."""
        message = TeamsMessage(
            text="/results",
            conversation_id="conv123",
            user_id="user456",
        )

        response = await processor.process_command(message)

        assert "Usage:" in response.message
        assert "/results {job_id}" in response.message

    @pytest.mark.asyncio
    async def test_process_results_command_not_found(self, processor):
        """Test /results command for non-existent job."""
        message = TeamsMessage(
            text="/results nonexistent",
            conversation_id="conv123",
            user_id="user456",
        )

        response = await processor.process_command(message)

        assert "Error" in response.message
        assert "not found" in response.message

    @pytest.mark.asyncio
    async def test_process_list_command_with_executions(self, processor):
        """Test /list command with active executions."""
        processor.active_executions["test-1"] = {
            "status": "completed",
            "execution_id": "exec-1",
            "started_at": "2024-01-15T10:00:00",
        }
        processor.active_executions["test-2"] = {
            "status": "running",
            "execution_id": "exec-2",
            "started_at": "2024-01-15T11:00:00",
        }

        message = TeamsMessage(
            text="/list",
            conversation_id="conv123",
            user_id="user456",
        )

        response = await processor.process_command(message)

        assert "Active Executions" in response.message
        assert "test-1" in response.message
        assert "test-2" in response.message

    @pytest.mark.asyncio
    async def test_process_list_command_empty(self, processor):
        """Test /list command with no executions."""
        message = TeamsMessage(
            text="/list",
            conversation_id="conv123",
            user_id="user456",
        )

        response = await processor.process_command(message)

        assert "No executions found" in response.message

    @pytest.mark.asyncio
    async def test_process_unknown_command(self, processor):
        """Test processing unknown command."""
        message = TeamsMessage(
            text="/unknown command",
            conversation_id="conv123",
            user_id="user456",
        )

        response = await processor.process_command(message)

        assert "Error" in response.message
        assert "Unknown command" in response.message

    @pytest.mark.asyncio
    async def test_process_empty_message(self, processor):
        """Test processing empty message returns help."""
        message = TeamsMessage(
            text="",
            conversation_id="conv123",
            user_id="user456",
        )

        response = await processor.process_command(message)

        assert "Vigil" in response.message

    @pytest.mark.asyncio
    async def test_process_whitespace_only_message(self, processor):
        """Test processing whitespace-only message returns help."""
        message = TeamsMessage(
            text="   ",
            conversation_id="conv123",
            user_id="user456",
        )

        response = await processor.process_command(message)

        assert "Vigil" in response.message

    @pytest.mark.asyncio
    async def test_command_case_insensitive(self, processor):
        """Test commands are case-insensitive."""
        message = TeamsMessage(
            text="/RUN test-123",  # Uppercase
            conversation_id="conv123",
            user_id="user456",
        )

        response = await processor.process_command(message)

        assert "test-123" in processor.active_executions
        assert processor.active_executions["test-123"]["status"] == "running"

    @pytest.mark.asyncio
    async def test_process_command_exception_handling(self, processor):
        """Test exceptions are caught and return error response."""
        # Mock the _handle_run_command to raise an exception
        processor._handle_run_command = AsyncMock(side_effect=Exception("Test error"))

        message = TeamsMessage(text="/run test-123", conversation_id="conv123")

        response = await processor.process_command(message)

        assert "Error" in response.message
        assert "something went wrong" in response.message.lower()

    def test_help_response_format(self, processor):
        """Test help response contains all commands."""
        response = processor._help_response()

        assert "/run" in response.message
        assert "/status" in response.message
        assert "/results" in response.message
        assert "/list" in response.message
        assert "/help" in response.message
        assert "Vigil" in response.message

    def test_error_response_format(self, processor):
        """Test error response format."""
        response = processor._error_response("Test error message")

        assert "Error" in response.message
        assert "Test error message" in response.message

    def test_url_trailing_slash_removed(self):
        """Test URLs have trailing slashes removed."""
        processor = TeamsCommandProcessor(
            executor_api_url="http://localhost:8001/",
            jira_api_url="http://localhost:8003/",
        )

        assert processor.executor_api_url == "http://localhost:8001"
        assert processor.jira_api_url == "http://localhost:8003"

    def test_active_executions_dict_initialized(self):
        """Test active executions dictionary is initialized."""
        processor = TeamsCommandProcessor(
            executor_api_url="http://localhost:8001",
            jira_api_url="http://localhost:8003",
        )

        assert isinstance(processor.active_executions, dict)
        assert len(processor.active_executions) == 0

    @pytest.mark.asyncio
    async def test_multiple_sequential_executions(self, processor):
        """Test multiple executions can be tracked."""
        # First execution
        message1 = TeamsMessage(text="/run test-1", conversation_id="conv1")
        await processor.process_command(message1)

        # Second execution
        message2 = TeamsMessage(text="/run test-2", conversation_id="conv1")
        await processor.process_command(message2)

        assert "test-1" in processor.active_executions
        assert "test-2" in processor.active_executions
        assert len(processor.active_executions) == 2

    @pytest.mark.asyncio
    async def test_run_with_special_characters_in_job_id(self, processor):
        """Test run command with special characters in job ID."""
        message = TeamsMessage(
            text="/run test_123-456.789",
            conversation_id="conv123",
        )

        response = await processor.process_command(message)

        assert "test_123-456.789" in processor.active_executions
        assert "test_123-456.789" in response.message

    @pytest.mark.asyncio
    async def test_results_without_jira_ticket(self, processor):
        """Test results command when no Jira ticket exists."""
        processor.active_executions["test-123"] = {
            "status": "completed",
            "execution_id": "exec-abc123",
            "started_at": datetime.utcnow().isoformat(),
        }

        message = TeamsMessage(text="/results test-123", conversation_id="conv123")

        response = await processor.process_command(message)

        assert "QA-XXX" in response.message or "N/A" in response.message

    @pytest.mark.asyncio
    async def test_help_response_with_adaptive_cards(self, processor_with_cards):
        """Test help response includes adaptive card when enabled."""
        message = TeamsMessage(text="/help", conversation_id="conv123")

        response = await processor_with_cards.process_command(message)

        assert response.response_type == "adaptive_card"
        assert response.adaptive_card is not None
        assert response.adaptive_card["type"] == "AdaptiveCard"

    @pytest.mark.asyncio
    async def test_run_command_with_adaptive_cards(self, processor_with_cards):
        """Test run command generates adaptive card when enabled."""
        message = TeamsMessage(
            text="/run test-123",
            conversation_id="conv123",
        )

        response = await processor_with_cards.process_command(message)

        assert response.response_type == "adaptive_card"
        assert response.adaptive_card is not None

    @pytest.mark.asyncio
    async def test_status_command_with_adaptive_cards(self, processor_with_cards):
        """Test status command generates adaptive card when enabled."""
        processor_with_cards.active_executions["test-123"] = {
            "status": "running",
            "execution_id": "exec-abc123",
            "started_at": datetime.utcnow().isoformat(),
        }

        message = TeamsMessage(text="/status test-123", conversation_id="conv123")

        response = await processor_with_cards.process_command(message)

        assert response.response_type == "adaptive_card"
        assert response.adaptive_card is not None

    @pytest.mark.asyncio
    async def test_results_command_with_adaptive_cards(self, processor_with_cards):
        """Test results command generates adaptive card when enabled."""
        processor_with_cards.active_executions["test-123"] = {
            "status": "completed",
            "execution_id": "exec-abc123",
            "started_at": datetime.utcnow().isoformat(),
        }

        message = TeamsMessage(text="/results test-123", conversation_id="conv123")

        response = await processor_with_cards.process_command(message)

        assert response.response_type == "adaptive_card"
        assert response.adaptive_card is not None

    @pytest.mark.asyncio
    async def test_list_command_with_adaptive_cards(self, processor_with_cards):
        """Test list command generates adaptive card when enabled."""
        message = TeamsMessage(text="/list", conversation_id="conv123")

        response = await processor_with_cards.process_command(message)

        assert response.response_type == "adaptive_card"
        assert response.adaptive_card is not None

    def test_card_formatter_lazy_loading(self, processor_with_cards):
        """Test card formatter is lazy loaded."""
        # Initially None
        assert processor_with_cards._card_formatter is None

        # Accessing the property should load it
        formatter = processor_with_cards.card_formatter

        assert formatter is not None
        assert processor_with_cards._card_formatter is not None

    def test_card_formatter_not_loaded_when_disabled(self, processor):
        """Test card formatter is not loaded when adaptive cards disabled."""
        # Accessing the property should return None
        formatter = processor.card_formatter

        assert formatter is None
        assert processor._card_formatter is None
