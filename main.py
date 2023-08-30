import json
import time

from utils import get_unique_word
from game import Game

from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
)

app = FastAPI()

class GameManager:
    
    def __init__(self):
        self.games = {}

    def game_exists(self, gamecode: str) -> bool:
        return gamecode in self.games
    
    def username_taken(self, gamecode: str, username: str) -> bool:
        game = self.games[gamecode]
        return any(player.username == username for player in game.players)
    
    def new_game(self, username, ws) -> str:
        gamecode = get_unique_word(self.games.keys())
        game = Game(gamecode, username, ws)
        self.games[gamecode] = game
        print(f"num games: {len(self.games)}")
        return gamecode
    
    async def join_game(self, gamecode, username, ws) -> Game:
        game = self.games[gamecode]
        await game.add_player(username, ws)
        return game
    
    def player_disconnect(self, gamecode, username):
        game = self.games[gamecode]
        game.player_disconnect(username)
        if game.over:
            del self.games[gamecode]

    
gm = GameManager()

@app.websocket("/")
async def websocket_endpoint(websocket: WebSocket, username: str, gamecode: str | None = None):

    # Accept connection by default
    await websocket.accept()

    # If joining an existing game, check if gamecode is valid and username is unique
    time.sleep(1) # TODO: will this reject other connection attempts?
    if gamecode:
        if not gm.game_exists(gamecode):
            await websocket.send_text(json.dumps({"type": "connect", "status": "error", "reason": "gamecode"}))
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
        gamecode = gm.new_game(username, websocket)
        game = gm.games[gamecode]

    # Send state
    state = game.get_state(username)
    await websocket.send_text(json.dumps(state))

    # Main loop
    try:
        while True:
            # Recieve update
            data = await websocket.receive_text()
            # Send update to game
            game.update(username, data)
    except WebSocketDisconnect:
        gm.player_disconnect(gamecode, username)