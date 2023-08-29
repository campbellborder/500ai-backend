import json

from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
)

app = FastAPI()

games = {"abcdefgh": ["pirate1", "pirate2"], "12345678": ["pirate1"]}

@app.websocket("/")
async def websocket_endpoint(websocket: WebSocket, username: str, gamecode: str | None = None):

    # Accept connection by default
    await websocket.accept()

    # If joining an existing game, check if gamecode is valid and username is unique
    if gamecode:
        if gamecode not in games:
            await websocket.send_text(json.dumps({"status": "error", "reason": "gamecode"}))
            await websocket.close()
            return
        if username in games[gamecode]:
            await websocket.send_text(json.dumps({"status": "error", "reason": "username"}))
            await websocket.close()
            return

    # Send success message
    await websocket.send_text(json.dumps({"status": "success"}))

    # If gamecode is null, start a new game

    # Else, add player to existing game


    # Default loop - remove
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(data)
    except WebSocketDisconnect:
        return