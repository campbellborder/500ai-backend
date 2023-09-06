import json
import time
from classes.game_manager import GameManager

from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
)

app = FastAPI()
gm = GameManager()

@app.websocket("/")
async def websocket_endpoint(websocket: WebSocket, username: str, gamecode: str | None = None):

    # Accept connection by default
    await websocket.accept()

    # If joining an existing game, check if gamecode is valid and username is unique
    time.sleep(1) # TODO: will this reject other connection attempts?
    if gamecode:
        if not gm.game_exists(gamecode):
            await websocket.send_text(json.dumps({"type": "connect", "status": "error", "reason": "no-game"}))
            await websocket.close()
            return
        if gm.game_full(gamecode):
            await websocket.send_text(json.dumps({"type": "connect", "status": "error", "reason": "game-full"}))
            await websocket.close()
            return
        if gm.username_taken(gamecode, username):
            await websocket.send_text(json.dumps({"type": "connect", "status": "error", "reason": "username"}))
            await websocket.close()
            return

    # Send success message
    await websocket.send_text(json.dumps({"type": "connect", "status": "success"}))

    # Add player to existing game
    if gamecode:
        game = await gm.join_game(gamecode, username, websocket)

    else: # Start a new game
        gamecode = await gm.new_game(username, websocket)
        game = gm.games[gamecode]

    # Main loop
    try:
        while True:
            # Recieve update
            data = await websocket.receive_text()
            update = json.loads(data)
            # Send update to game
            await game.update(username, update)
            await game.ai_update()

            if game.is_over():
                print("game_over")
            

    except WebSocketDisconnect:
        await gm.player_disconnect(gamecode, username)