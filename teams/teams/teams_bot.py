"""
Microsoft Teams Bot for Vigil Test Executor.

Handles incoming Teams messages and orchestrates command processing.
"""

import os
import logging
from typing import Optional

from botbuilder.core import ActivityHandler, TurnContext, CardFactory
from botbuilder.schema import Activity, ActivityTypes


logger = logging.getLogger(__name__)


class TeamsBot(ActivityHandler):
    """
    Microsoft Teams bot for handling test execution commands.

    This bot receives messages from Teams and processes them
    through the command processor to trigger and manage test executions.
    """

    def __init__(self, command_processor: "CommandProcessor"):
        """
        Initialize the Teams bot.

        Args:
            command_processor: Instance to process Teams commands
        """
        self.command_processor = command_processor
        logger.info("TeamsBot initialized")

    async def on_message_activity(self, turn_context: TurnContext):
        """
        Handle incoming message activity from Teams.

        Args:
            turn_context: The turn context for this activity
        """
        try:
            # Extract message text
            text = turn_context.activity.text.strip() if turn_context.activity.text else ""

            if not text:
                return

            # Get user information
            from_address = turn_context.activity.from_property

            # Process command through command processor
            response = await self.command_processor.process_command(
                text=text,
                user_id=from_address.id if from_address else None,
                user_name=from_address.name if from_address else None,
                conversation_id=turn_context.activity.conversation.id,
            )

            # Send response back to Teams
            await turn_context.send_activity(response.message)

        except Exception as e:
            logger.error(f"Error handling message activity: {e}")
            await turn_context.send_activity(
                f"Sorry, something went wrong. Please try again later."
            )

    async def on_teams_conversation_update_activity(self, turn_context: TurnContext):
        """
        Handle when bot is added to a conversation.

        Args:
            turn_context: The turn context for this activity
        """
        # Send welcome message when bot is added
        welcome_text = """Welcome to Vigil Test Executor Bot!

Available commands:
- /run {job_id} - Execute a test
- /status {job_id} - Check execution status
- /results {job_id} - Get execution results
- /list - List all executions
- /help - Show help message

Type /help to see detailed usage instructions.
"""
        await turn_context.send_activity(welcome_text)
        logger.info(f"Bot added to conversation: {turn_context.activity.conversation.id}")
