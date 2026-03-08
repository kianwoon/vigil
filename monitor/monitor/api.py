"""
Monitor API endpoints.

Provides REST API for controlling the monitoring sidecar.
"""

import os
from datetime import datetime
from typing import Optional
import logging

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from playwright.async_api import async_playwright

from models import BrowserMetrics
from metrics_collector import MetricsCollector
from websocket_server import MetricsWebSocketServer


logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="NanoClaw Monitor API",
    description="Browser health monitoring sidecar for NanoClaw executor",
    version="1.0.0",
)

# Global state
collector: Optional[MetricsCollector] = None
websocket_server: Optional[MetricsWebSocketServer] = None
playwright_instance = None


# Request models
class StartMonitoringRequest(BaseModel):
    """Request to start monitoring."""
    browser_ws_endpoint: str  # Playwright browser WebSocket endpoint
    sample_interval_ms: int = 100


class StopMonitoringResponse(BaseModel):
    """Response when stopping monitoring."""
    status: str
    summary: dict


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize monitor service on startup."""
    global collector, websocket_server

    logger.info("Starting NanoClaw Monitor service")

    # Initialize metrics collector
    collector = MetricsCollector(
        sample_interval_ms=int(os.getenv("MONITOR_SAMPLE_INTERVAL_MS", "100")),
        enable_cdp=True,
        enable_psutil=True,
    )

    # Initialize WebSocket server
    host = os.getenv("MONITOR_HOST", "0.0.0.0")
    port = int(os.getenv("MONITOR_PORT", "8002"))
    websocket_server = MetricsWebSocketServer(host=host, port=port)

    # Start WebSocket server
    await websocket_server.start()

    logger.info("NanoClaw Monitor service started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global collector, websocket_server

    logger.info("Shutting down NanoClaw Monitor service")

    # Stop metrics collector
    if collector and collector.is_collecting:
        await collector.stop()

    # Stop WebSocket server
    if websocket_server:
        await websocket_server.stop()

    logger.info("NanoClaw Monitor service stopped")


# API endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "nanoclaw-monitor",
        "timestamp": datetime.utcnow().isoformat(),
        "collector_active": collector.is_collecting if collector else False,
        "websocket_clients": len(websocket_server.clients) if websocket_server else 0,
    }


@app.post("/api/v1/monitoring/start")
async def start_monitoring(request: StartMonitoringRequest, background_tasks: BackgroundTasks):
    """
    Start monitoring a browser instance.

    Args:
        request: Start monitoring request
        background_tasks: FastAPI background tasks

    Returns:
        Confirmation that monitoring has started
    """
    if not collector or not websocket_server:
        raise HTTPException(status_code=503, detail="Monitor service not initialized")

    if collector.is_collecting:
        raise HTTPException(status_code=400, detail="Monitoring already active")

    try:
        # Connect to browser via CDP (WebSocket endpoint)
        # Note: This is a simplified version
        # Actual implementation would connect to Playwright's browser instance

        # Start metrics collection with WebSocket streaming
        async def stream_metrics(metrics: BrowserMetrics):
            await websocket_server.broadcast_metrics(metrics)

        background_tasks.add_task(collector.start_streaming, stream_metrics)

        return {
            "status": "started",
            "message": "Monitoring started successfully",
            "sample_interval_ms": request.sample_interval_ms,
            "websocket_uri": websocket_server.uri,
        }

    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {str(e)}")


@app.post("/api/v1/monitoring/stop", response_model=StopMonitoringResponse)
async def stop_monitoring():
    """
    Stop monitoring and return summary.

    Returns:
        Summary of collected metrics
    """
    if not collector or not collector.is_collecting:
        raise HTTPException(status_code=400, detail="Monitoring not active")

    try:
        summary = await collector.stop()

        return StopMonitoringResponse(
            status="stopped",
            summary=summary,
        )

    except Exception as e:
        logger.error(f"Failed to stop monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop monitoring: {str(e)}")


@app.get("/api/v1/monitoring/errors")
async def get_error_details():
    """
    Get detailed error information from current monitoring session.

    Returns:
        Network and console errors collected
    """
    if not collector:
        raise HTTPException(status_code=503, detail="Monitor service not initialized")

    try:
        errors = collector.get_error_details()
        return {
            "status": "success",
            "data": errors,
        }

    except Exception as e:
        logger.error(f"Failed to get error details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get error details: {str(e)}")


@app.post("/api/v1/monitoring/clear")
async def clear_monitoring_data():
    """
    Clear all monitoring data buffers.

    Returns:
        Confirmation that data was cleared
    """
    if not collector:
        raise HTTPException(status_code=503, detail="Monitor service not initialized")

    try:
        collector.clear_buffers()
        return {
            "status": "cleared",
            "message": "Monitoring data buffers cleared",
        }

    except Exception as e:
        logger.error(f"Failed to clear monitoring data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear monitoring data: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "NanoClaw Monitor",
        "version": "1.0.0",
        "description": "Browser health monitoring sidecar for NanoClaw executor",
        "endpoints": {
            "health": "/health",
            "start_monitoring": "POST /api/v1/monitoring/start",
            "stop_monitoring": "POST /api/v1/monitoring/stop",
            "get_errors": "GET /api/v1/monitoring/errors",
            "clear_data": "POST /api/v1/monitoring/clear",
            "websocket": f"ws://{os.getenv('MONITOR_HOST', '0.0.0.0')}:{os.getenv('MONITOR_PORT', '8002')}",
        },
        "docs": "/docs",
    }
