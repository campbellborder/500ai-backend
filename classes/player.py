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