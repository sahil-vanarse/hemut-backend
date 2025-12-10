from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging
import json
import os
from websocket import manager
from routes import auth_routes, question_routes, answer_routes

# Initialize FastAPI app
app = FastAPI(title="Hemut Q&A Dashboard API")
logger = logging.getLogger("uvicorn.error")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(auth_routes.router)
app.include_router(question_routes.router)
app.include_router(answer_routes.router)


# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Hemut Q&A Dashboard API", "status": "running"}


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print("New WebSocket connection attempt from:", websocket.client)
    try:
        await manager.connect(websocket)
        print(f"✅ WebSocket connected. Total connections: {len(manager.active_connections)}")
    except Exception as e:
        print(f"❌ Error connecting WebSocket: {e}")
        return
    try:
        while True:
            try:
                # Wait for message with timeout to keep connection alive
                data = await websocket.receive_text()
                print(f"Received WebSocket message: {data}")
                # Echo received messages (can be used for ping/pong)
                await websocket.send_text(json.dumps({"type": "pong", "data": data}))
            except Exception as e:
                print(f"Error in WebSocket receive loop: {e}")
                # If there's an error receiving, break the loop
                break
    except WebSocketDisconnect:
        print("WebSocket disconnected normally")
    finally:
        manager.disconnect(websocket)
        print(f"WebSocket cleaned up. Remaining connections: {len(manager.active_connections)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)