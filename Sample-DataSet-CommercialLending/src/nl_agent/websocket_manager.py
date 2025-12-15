"""
WebSocket Manager for real-time workflow status updates.
Manages WebSocket connections and broadcasts messages to connected clients.
"""

import json
import asyncio
from typing import Dict, List
from fastapi import WebSocket
from datetime import datetime


class WebSocketManager:
    """Manages WebSocket connections grouped by run_id."""

    def __init__(self):
        # Dictionary mapping run_id to list of WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, run_id: str, websocket: WebSocket):
        """Accept a new WebSocket connection for a specific run_id."""
        await websocket.accept()

        if run_id not in self.active_connections:
            self.active_connections[run_id] = []

        self.active_connections[run_id].append(websocket)
        print(f"WebSocketManager: Client connected to run_id={run_id}. Total connections: {len(self.active_connections[run_id])}")

        # Send connection acknowledgment
        await self.send_personal_message(websocket, {
            "type": "connection_established",
            "run_id": run_id,
            "message": "Connected to workflow updates",
            "timestamp": datetime.utcnow().isoformat()
        })

    async def disconnect(self, run_id: str, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if run_id in self.active_connections:
            if websocket in self.active_connections[run_id]:
                self.active_connections[run_id].remove(websocket)
                print(f"WebSocketManager: Client disconnected from run_id={run_id}. Remaining: {len(self.active_connections[run_id])}")

            # Clean up empty run_id entries
            if len(self.active_connections[run_id]) == 0:
                del self.active_connections[run_id]

    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """Send a message to a specific WebSocket connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"WebSocketManager: Error sending personal message: {e}")

    async def broadcast(self, run_id: str, message: dict):
        """
        Broadcast a message to all WebSocket clients connected to a specific run_id.

        Args:
            run_id: The workflow run identifier
            message: Dictionary containing the message data
        """
        if run_id not in self.active_connections:
            print(f"WebSocketManager: No active connections for run_id={run_id}")
            return

        # Add timestamp to message
        message["timestamp"] = datetime.utcnow().isoformat()

        print(f"WebSocketManager: Broadcasting to {len(self.active_connections[run_id])} clients for run_id={run_id}")
        print(f"WebSocketManager: Message: {json.dumps(message, indent=2)}")

        # Send to all connected clients for this run_id
        disconnected_clients = []

        for connection in self.active_connections[run_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"WebSocketManager: Error broadcasting to client: {e}")
                disconnected_clients.append(connection)

        # Remove disconnected clients
        for connection in disconnected_clients:
            await self.disconnect(run_id, connection)

    def get_connection_count(self, run_id: str) -> int:
        """Get the number of active connections for a run_id."""
        if run_id in self.active_connections:
            return len(self.active_connections[run_id])
        return 0

    def get_all_run_ids(self) -> List[str]:
        """Get all run_ids with active connections."""
        return list(self.active_connections.keys())


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
