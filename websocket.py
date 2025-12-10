from fastapi import WebSocket
from typing import List


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        disconnected = []
        print(f"Broadcasting to {len(self.active_connections)} connections: {message.get('type')}")
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
                print(f"Successfully sent {message.get('type')} to connection")
            except Exception as e:
                print(f"Error sending message: {e}")
                disconnected.append(connection)
        # Remove disconnected connections
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)


# Global connection manager instance
manager = ConnectionManager()
