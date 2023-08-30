import json
from fastapi import (
    WebSocket
)

class Player():

    def __init__(self, username: str, ws: WebSocket, position: str, host: bool = False):
        self.username = username
        self.ws = ws
        self.position = position
        self.host = host

    def get_state_repr(player, you, position = None):
        if player is None:
            return {
                "position": position,
                "type": "empty"
            }
        return {
            "position": player.position,
            "type": "human",
            "username": player.username,
            "host": player.host,
            "you": player.username == you
        }

class Game:
    
    positions = ["N", "E", "S", "W"]

    def __init__(self, gamecode, username, ws):
        
        self.gamecode = gamecode
        self.players = [Player(username, ws, Game.positions[0], host=True)]
        self.over = False
        self.state = "setup"

    async def add_player(self, username, ws):
        for position in Game.positions:
            if position not in self._taken_positions():
              player = Player(username, ws, position)
              self.players.append(player)
              break
        
        for otherPlayer in self.players:
            if otherPlayer != player:
                await otherPlayer.ws.send_text(json.dumps(self.get_state(otherPlayer.username)))

    def _taken_positions(self):
        return [player.position for player in self.players]

    def player_disconnect(self, username):
        raise NotImplementedError
        if self.players[username].host: # Wont work players in list
            # Host has left, destroy game
            self.over = True
            for player in self.players:
                player.ws.close()
            
        else: # Substitute AI for player
            pass
        
    def get_state(self, username):
        if self.state == "setup":
            state = {}
            state["state"] = self.state
            state["gamecode"] = self.gamecode
            state["players"] = [Player.get_state_repr(player, username) for player in self.players]
            for position in set(Game.positions) - set(self._taken_positions()):
                state["players"].append(Player.get_state_repr(None, None, position))
            return state
