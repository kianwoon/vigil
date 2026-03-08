"""
Teams Integration API endpoints.

Provides API for Microsoft Teams bot webhook and service management.
"""

import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel


logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Vigil Teams Integration API",
    description="Microsoft Teams bot interface for Vigil Test Executor",
    version="1.0.0",
)

# Global state
teams_bot: Optional["TeamsBot"] = None
command_processor: Optional["CommandProcessor"] = None


# Request models
class SendMessageRequest(BaseModel):
    """Request to send message to Teams."""
    conversation_id: str
    message: str
    message_type: str = "text"


class TriggerExecutionRequest(BaseModel):
    """Request to trigger test execution via Teams."""
    job_id: str
    conversation_id: str
    user_id: Optional[str] = None


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize Teams service on startup."""
    global teams_bot, command_processor

    logger.info("Starting Vigil Teams Integration service")

    # Initialize command processor
    from command_processor import CommandProcessor

    executor_api_url = os.getenv("EXECUTOR_API_URL", "http://executor:8000")
    jira_api_url = os.getenv("JIRA_API_URL", "http://jira-integrator:8001")

    command_processor = CommandProcessor(
        executor_api_url=executor_api_url,
        jira_api_url=jira_api_url,
    )

    # Initialize Teams bot
    from teams_bot import TeamsBot

    teams_bot = TeamsBot(command_processor=command_processor)

    logger.info("Vigil Teams Integration service started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Vigil Teams Integration service")
    logger.info("Vigil Teams Integration service stopped")


# API endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "vigil-teams-integration",
        "timestamp": datetime.utcnow().isoformat(),
        "bot_configured": teams_bot is not None,
    }


@app.post("/api/v1/teams/webhook")
async def teams_webhook(request: Request):
    """
    Handle incoming Teams webhook messages.

    This endpoint receives messages from Microsoft Teams via the Bot Framework.

    Args:
        request: Incoming webhook request

    Returns:
        200 OK response
    """
    if not teams_bot:
        raise HTTPException(
            status_code=503,
            detail="Teams bot service not fully initialized"
        )

    try:
        # Parse incoming activity
        body = await request.json()
        activity = Activity(**body)

        # Process activity through bot
        # Note: In production, use botframework-connector library
        # to handle authentication and proper activity processing

        logger.info(f"Received Teams activity: {activity.type}")

        # For now, return 200
        # Actual processing would be done by Bot Framework adapter
        return {"status": "received"}

    except Exception as e:
        logger.error(f"Failed to process Teams webhook: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process webhook: {str(e)}"
        )


@app.post("/api/v1/teams/send")
async def send_message(request: SendMessageRequest, background_tasks: BackgroundTasks):
    """
    Send a message to a Teams conversation.

    Args:
        request: Message details
        background_tasks: FastAPI background tasks

    Returns:
        Confirmation of message sent
    """
    if not command_processor:
        raise HTTPException(
            status_code=503,
            detail="Teams service not fully initialized"
        )

    try:
        # In production, use Bot Framework connector to send message
        # For now, just log and return success

        logger.info(f"Sending message to conversation {request.conversation_id}")

        return {
            "status": "success",
            "message": "Message queued for delivery",
            "conversation_id": request.conversation_id,
        }

    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send message: {str(e)}"
        )


@app.post("/api/v1/teams/trigger")
async def trigger_execution(request: TriggerExecutionRequest):
    """
    Trigger a test execution and notify via Teams.

    Args:
        request: Execution trigger details

    Returns:
        Execution confirmation
    """
    if not command_processor:
        raise HTTPException(
            status_code=503,
            detail="Teams service not fully initialized"
        )

    try:
        # Process run command
        response = await command_processor.process_command(
            text=f"/run {request.job_id}",
            user_id=request.user_id,
            conversation_id=request.conversation_id,
        )

        return {
            "status": "success",
            "message": response.message,
            "job_id": request.job_id,
        }

    except Exception as e:
        logger.error(f"Failed to trigger execution: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger execution: {str(e)}"
        )


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "NanoClaw Teams Integration",
        "version": "1.0.0",
        "description": "Microsoft Teams bot interface for NanoClaw Test Executor",
        "endpoints": {
            "health": "/health",
            "webhook": "POST /api/v1/teams/webhook",
            "send_message": "POST /api/v1/teams/send",
            "trigger_execution": "POST /api/v1/teams/trigger",
        },
        "docs": "/docs",
    }
