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

async def create_game(gamecode, username, ws):
    game = Game(gamecode, username, ws)
    await game._init()
    return game

class Game:
    
    positions = ["N", "E", "S", "W"]

    def __init__(self, gamecode, username, ws):
        
        self.gamecode = gamecode
        self.players = [Player(username, ws, Game.positions[0], host=True)]
        self.over = False
        self.state = "setup"
    
    async def _init(self):
        await self._broadcast_state()

    async def add_player(self, username, ws):
        for position in Game.positions:
            if position not in self._taken_positions():
              player = Player(username, ws, position)
              self.players.append(player)
              break
        
        await self._broadcast_state()

    def _get_player(self, username):
        return next(player for player in self.players if player.username == username)

    def _taken_positions(self):
        return [player.position for player in self.players]

    async def _broadcast_state(self):
        for player in self.players:
            await player.ws.send_text(json.dumps(self.get_state_message(player.username)))

    async def update(self, username, update):
        if update["state"] == self.state:
            action = update["action"]
            match action["type"]:
                case "move-position":
                    print("moving")
                    self._get_player(username).position = action["position"]
                case _:
                    pass

        await self._broadcast_state()

    async def player_disconnect(self, username):
        
        player = self._get_player(username)
        self.players.remove(player)

        if not len(self.players): 
            # Only player has left, destroy game
            self.over = True
            for player in self.players:
                await player.ws.close()
            return

        # TODO: Send player left alert

        if player.host:
            # Host has left, new host
            self.players[0].host = True
            # TODO: Send new host alert

        if self.state == "play":
            # Substitute AI for player
            raise NotImplementedError

        await self._broadcast_state()
        
    def get_state_message(self, username):
        if self.state == "setup":
            message = {}
            message["type"] = "state"
            message["state"] = self.state
            message["gamecode"] = self.gamecode
            message["players"] = [Player.get_state_repr(player, username) for player in self.players]
            for position in set(Game.positions) - set(self._taken_positions()):
                message["players"].append(Player.get_state_repr(None, None, position))
            return message
        else:
            raise NotImplementedError
