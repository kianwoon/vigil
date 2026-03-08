"""
Jira Integrator API endpoints.

Provides API for posting test results to Jira.
"""

import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from models import ExecutionResult
from client import JiraClient
from formatter import JiraCommentFormatter
from evidence_packager import EvidencePackager


logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Vigil Jira Integrator API",
    description="Posts test results and evidence packages to Jira",
    version="1.0.0",
)

# Global state
jira_client: Optional[JiraClient] = None
formatter: Optional[JiraCommentFormatter] = None
packager: Optional[EvidencePackager] = None


# Request models
class PostResultRequest(BaseModel):
    """Request to post execution result to Jira."""
    execution_id: str
    job_id: str
    jira_ticket: str
    test_result: str
    health_grade: str
    duration_seconds: float
    peak_memory_mb: float
    peak_cpu_percent: float
    total_network_errors: int
    total_console_errors: int
    total_console_warnings: int
    trace_path: Optional[str] = None
    logs_path: Optional[str] = None
    screenshot_path: Optional[str] = None
    issues: list = []
    warnings: list = []


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize Jira integrator service on startup."""
    global jira_client, formatter, packager

    logger.info("Starting Vigil Jira Integrator service")

    # Initialize Jira client
    jira_client = JiraClient()

    # Initialize formatter
    formatter = JiraCommentFormatter()

    # Initialize packager
    output_dir = os.getenv("SHARED_RESULTS_DIR", "./shared/results")
    packager = EvidencePackager(output_dir)

    logger.info("Vigil Jira Integrator service started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global jira_client

    logger.info("Shutting down Vigil Jira Integrator service")

    if jira_client:
        await jira_client.close()

    logger.info("Vigil Jira Integrator service stopped")


# API endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "vigil-jira-integrator",
        "timestamp": datetime.utcnow().isoformat(),
        "jira_configured": jira_client is not None,
    }


@app.post("/api/v1/jira/post")
async def post_result_to_jira(request: PostResultRequest):
    """
    Post execution result to Jira ticket.

    Args:
        request: Execution result details

    Returns:
        Confirmation of posting
    """
    if not jira_client or not formatter:
        raise HTTPException(
            status_code=503,
            detail="Jira integrator service not fully initialized"
        )

    try:
        # Create ExecutionResult from request
        from models import ExecutionStatus, TestResult, HealthGrade, HealthAnalysis

        result = ExecutionResult(
            execution_id=request.execution_id,
            job_id=request.job_id,
            jira_ticket=request.jira_ticket,
            status=ExecutionStatus.COMPLETED,
            test_result=TestResult(request.test_result),
            health_analysis=HealthAnalysis(
                grade=HealthGrade(request.health_grade),
                issues=request.issues,
                warnings=request.warnings,
            ),
            started_at=datetime.utcnow(),  # Approximate
            completed_at=datetime.utcnow(),
            duration_seconds=request.duration_seconds,
            peak_memory_mb=request.peak_memory_mb,
            peak_cpu_percent=request.peak_cpu_percent,
            total_network_errors=request.total_network_errors,
            total_console_errors=request.total_console_errors,
            total_console_warnings=request.total_console_warnings,
            trace_path=request.trace_path,
            logs_path=request.logs_path,
            screenshot_path=request.screenshot_path,
        )

        # Format comment
        comment = formatter.format_execution_result(result)
        comment_markdown = comment.to_markdown()

        # Post comment to Jira
        await jira_client.post_comment(
            ticket_id=request.jira_ticket,
            comment=comment_markdown,
        )

        # Attach evidence files if they exist
        attachments = []
        if request.trace_path:
            attachments.append(request.trace_path)
        if request.logs_path:
            attachments.append(request.logs_path)

        # Attach metrics and health report
        exec_dir = packager.output_dir / request.execution_id
        if exec_dir.exists():
            metrics_csv = exec_dir / "metrics.csv"
            health_report = exec_dir / "health_report.json"

            if metrics_csv.exists():
                attachments.append(str(metrics_csv))
            if health_report.exists():
                attachments.append(str(health_report))

        if attachments:
            await jira_client.add_attachments(request.jira_ticket, attachments)

        return {
            "status": "success",
            "message": f"Result posted to {request.jira_ticket}",
            "jira_ticket": request.jira_ticket,
            "attachments_count": len(attachments),
        }

    except Exception as e:
        logger.error(f"Failed to post result to Jira: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to post to Jira: {str(e)}"
        )


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "NanoClaw Jira Integrator",
        "version": "1.0.0",
        "description": "Posts test results and evidence packages to Jira",
        "endpoints": {
            "health": "/health",
            "post_result": "POST /api/v1/jira/post",
        },
        "docs": "/docs",
    }
