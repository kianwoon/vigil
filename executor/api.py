"""
Executor API endpoints.

Provides REST API for triggering and managing test executions.
"""

import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Request
from pydantic import BaseModel

from models import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)
from runner import TestRunner
from whatsapp_interface import (
    WhatsAppCommandProcessor,
    WhatsAppMessage,
    WhatsAppResponse,
)


logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Vigil Executor API",
    description="Runtime health auditor with health monitoring",
    version="1.0.0",
)

# Global state
runner: Optional[TestRunner] = None
whatsapp_processor: Optional[WhatsAppCommandProcessor] = None
active_executions: dict = {}


# Request models
class ExecutionRequestModel(BaseModel):
    """Execution request model."""
    job_id: str
    jira_ticket: str
    script_path: str
    timeout_seconds: int = 300
    browser_headless: bool = True
    trace_enabled: bool = True


class StatusResponse(BaseModel):
    """Status response model."""
    execution_id: str
    status: str
    test_result: Optional[str] = None
    health_grade: Optional[str] = None
    duration_seconds: float
    error: Optional[str] = None


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize executor service on startup."""
    global runner, whatsapp_processor

    logger.info("Starting Vigil Executor service")

    # Initialize test runner
    shared_scripts = os.getenv("SHARED_SCRIPTS_DIR", "./shared/scripts")
    shared_results = os.getenv("SHARED_RESULTS_DIR", "./shared/results")
    monitor_ws = os.getenv("MONITOR_WS_URL", "ws://monitor:8002")

    runner = TestRunner(
        shared_scripts_dir=shared_scripts,
        shared_results_dir=shared_results,
        monitor_ws_url=monitor_ws,
    )

    # Initialize WhatsApp command processor
    executor_url = f"http://{os.getenv('EXECUTOR_HOST', 'localhost')}:{os.getenv('EXECUTOR_PORT', '8001')}"
    jira_url = f"http://{os.getenv('JIRA_INTEGRATOR_HOST', 'localhost')}:{os.getenv('JIRA_INTEGRATOR_PORT', '8003')}"

    whatsapp_processor = WhatsAppCommandProcessor(
        executor_api_url=executor_url,
        jira_api_url=jira_url,
    )

    logger.info("Vigil Executor service started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Vigil Executor service")


# API endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "vigil-executor",
        "timestamp": datetime.utcnow().isoformat(),
        "active_executions": len(active_executions),
    }


@app.post("/api/v1/execute")
async def execute_test(
    request: ExecutionRequestModel,
    background_tasks: BackgroundTasks,
):
    """
    Execute a test script with health monitoring.

    Args:
        request: Execution request
        background_tasks: FastAPI background tasks

    Returns:
        Execution confirmation with execution_id
    """
    if not runner:
        raise HTTPException(status_code=503, detail="Executor service not initialized")

    # Check if job already running
    if request.job_id in active_executions:
        raise HTTPException(
            status_code=400,
            detail=f"Job {request.job_id} is already running"
        )

    try:
        # Create execution request
        exec_request = ExecutionRequest(
            job_id=request.job_id,
            jira_ticket=request.jira_ticket,
            script_path=request.script_path,
            timeout_seconds=request.timeout_seconds,
            browser_headless=request.browser_headless,
            trace_enabled=request.trace_enabled,
        )

        # Execute in background
        background_tasks.add_task(execute_and_store, exec_request)

        return {
            "status": "accepted",
            "message": "Test execution started",
            "job_id": request.job_id,
            "jira_ticket": request.jira_ticket,
        }

    except Exception as e:
        logger.error(f"Failed to start execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def execute_and_store(request: ExecutionRequest) -> None:
    """
    Execute test and store result in active_executions.

    Args:
        request: Execution request
    """
    global active_executions

    try:
        active_executions[request.job_id] = {
            "status": ExecutionStatus.RUNNING,
            "started_at": datetime.utcnow(),
        }

        # Run execution
        result = await runner.execute(request)

        # Store result
        active_executions[request.job_id] = {
            "status": result.status,
            "result": result,
            "completed_at": datetime.utcnow(),
        }

        logger.info(f"Execution {result.execution_id} completed")

    except Exception as e:
        logger.error(f"Execution failed: {e}")
        active_executions[request.job_id] = {
            "status": ExecutionStatus.FAILED,
            "error": str(e),
            "completed_at": datetime.utcnow(),
        }


@app.get("/api/v1/status/{job_id}", response_model=StatusResponse)
async def get_execution_status(job_id: str):
    """
    Get execution status for a job.

    Args:
        job_id: Job ID to check

    Returns:
        Current execution status
    """
    execution = active_executions.get(job_id)

    if not execution:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if execution["status"] == ExecutionStatus.RUNNING:
        return StatusResponse(
            execution_id=job_id,
            status=execution["status"].value,
            duration_seconds=(
                datetime.utcnow() - execution["started_at"]
            ).total_seconds(),
        )

    # Execution completed
    result = execution.get("result")
    if result:
        return StatusResponse(
            execution_id=result.execution_id,
            status=result.status.value,
            test_result=result.test_result.value,
            health_grade=result.health_analysis.grade.value if result.health_analysis else None,
            duration_seconds=result.duration_seconds,
            error=result.error_message,
        )

    # Execution failed
    return StatusResponse(
        execution_id=job_id,
        status=execution["status"].value,
        duration_seconds=0,
        error=execution.get("error"),
    )


@app.get("/api/v1/result/{job_id}")
async def get_execution_result(job_id: str):
    """
    Get detailed execution result.

    Args:
        job_id: Job ID to get result for

    Returns:
        Detailed execution result
    """
    execution = active_executions.get(job_id)

    if not execution:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if execution["status"] == ExecutionStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is still running"
        )

    result = execution.get("result")
    if not result:
        raise HTTPException(
            status_code=500,
            detail=execution.get("error", "Execution failed"),
        )

    return result.to_summary_dict()


@app.get("/api/v1/trace/{execution_id}")
async def get_trace_viewer(execution_id: str):
    """
    Get Playwright trace file for viewing.

    Args:
        execution_id: Execution ID to get trace for

    Returns:
        Trace file path and viewing instructions
    """
    # Find execution by execution_id
    for job_id, execution in active_executions.items():
        result = execution.get("result")
        if result and result.execution_id == execution_id:
            if result.trace_path:
                return {
                    "execution_id": execution_id,
                    "trace_path": result.trace_path,
                    "viewing_instructions": {
                        "method1": "Open in Chrome: chrome://tracing → Load trace file",
                        "method2": "Playwright CLI: npx playwright show-trace <trace-path>",
                        "method3": "VS Code: Open trace.zip with Playwright extension",
                    },
                }
            else:
                raise HTTPException(
                    status_code=404,
                    detail="No trace file available for this execution"
                )

    raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")


# WhatsApp webhook endpoints
@app.post("/api/v1/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    """
    Handle incoming WhatsApp webhook messages.

    Expects JSON payload with:
    - phone_number: Sender's phone number
    - message_body: Message text
    - message_id: Optional message ID
    - timestamp: Optional timestamp

    Returns:
        Response message to send back via WhatsApp
    """
    if not whatsapp_processor:
        raise HTTPException(
            status_code=503,
            detail="WhatsApp processor not initialized"
        )

    try:
        # Parse incoming webhook payload
        payload = await request.json()

        phone_number = payload.get("phone_number")
        message_body = payload.get("message_body")
        message_id = payload.get("message_id")

        if not phone_number or not message_body:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: phone_number, message_body"
            )

        # Create WhatsApp message
        message = WhatsAppMessage(
            phone_number=phone_number,
            message_body=message_body,
            message_id=message_id,
        )

        # Process command
        response = await whatsapp_processor.process_command(message)

        logger.info(f"Processed WhatsApp command from {phone_number}: {message_body[:50]}")

        return response.to_dict()

    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process webhook: {str(e)}"
        )


@app.get("/api/v1/whatsapp/health")
async def whatsapp_health_check():
    """WhatsApp interface health check."""
    return {
        "status": "healthy" if whatsapp_processor else "unavailable",
        "service": "vigil-whatsapp-interface",
        "timestamp": datetime.utcnow().isoformat(),
        "active_executions": len(whatsapp_processor.active_executions) if whatsapp_processor else 0,
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Vigil Executor",
        "version": "1.0.0",
        "description": "Runtime health auditor with health monitoring",
        "endpoints": {
            "health": "/health",
            "execute": "POST /api/v1/execute",
            "status": "GET /api/v1/status/{job_id}",
            "result": "GET /api/v1/result/{job_id}",
            "trace": "GET /api/v1/trace/{execution_id}",
            "whatsapp_webhook": "POST /api/v1/whatsapp/webhook",
            "whatsapp_health": "GET /api/v1/whatsapp/health",
        },
        "docs": "/docs",
    }
