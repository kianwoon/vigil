"""
WebSocket server for real-time metrics streaming.

Streams browser health metrics to connected executor clients.
"""

import asyncio
import json
import logging
from typing import Set, Optional
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol

from models import BrowserMetrics


logger = logging.getLogger(__name__)


class MetricsWebSocketServer:
    """
    WebSocket server for streaming browser metrics.

    Allows executor to subscribe to real-time metric updates
    from the monitoring sidecar.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8002):
        """
        Initialize WebSocket server.

        Args:
            host: Server host address
            port: Server port
        """
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.server: Optional[websockets.WebSocketServer] = None
        self.is_running = False

    async def handle_client(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """
        Handle individual WebSocket client connection.

        Args:
            websocket: WebSocket client connection
            path: WebSocket URL path
        """
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"Client connected: {client_id}")

        self.clients.add(websocket)

        try:
            # Send welcome message
            await websocket.send(json.dumps({
                "type": "connected",
                "message": "Connected to NanoClaw metrics stream",
                "timestamp": datetime.utcnow().isoformat(),
            }))

            # Keep connection alive and handle incoming messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    logger.debug(f"Received from {client_id}: {data}")

                    # Handle client commands
                    if data.get("type") == "ping":
                        await websocket.send(json.dumps({
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat(),
                        }))

                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from {client_id}: {message}")
                except Exception as e:
                    logger.error(f"Error handling message from {client_id}: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        finally:
            self.clients.discard(websocket)

    async def broadcast_metrics(self, metrics: BrowserMetrics) -> None:
        """
        Broadcast metrics to all connected clients.

        Args:
            metrics: Browser metrics to broadcast
        """
        if not self.clients:
            return

        message = json.dumps({
            "type": "metrics",
            "data": metrics.to_dict(),
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Send to all connected clients
        disconnected = set()
        for client in self.clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected.add(client)

        # Remove disconnected clients
        self.clients -= disconnected

    async def start(self) -> None:
        """Start the WebSocket server."""
        if self.is_running:
            logger.warning("WebSocket server already running")
            return

        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")

        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=20,
        )

        self.is_running = True
        logger.info("WebSocket server started")

    async def stop(self) -> None:
        """Stop the WebSocket server."""
        if not self.is_running:
            return

        logger.info("Stopping WebSocket server")

        # Close all client connections
        for client in self.clients:
            await client.close()

        self.clients.clear()

        if self.server:
            self.server.close()
            await self.server.wait_closed()

        self.is_running = False
        logger.info("WebSocket server stopped")

    @property
    def uri(self) -> str:
        """Get WebSocket server URI."""
        return f"ws://{self.host}:{self.port}"
