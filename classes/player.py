from fastapi import (
    WebSocket
)
import json
from rlcard.games.five_hundred.utils.five_hundred_card import FiveHundredCard
from rlcard.games.five_hundred.utils.move import CallMove
from rlcard.games.five_hundred.utils.action_event import ActionEvent

def custom_serializer(obj):
    if isinstance(obj, FiveHundredCard):
        return obj.__repr__()
    if isinstance(obj, CallMove):
        return obj.__repr__()
    if isinstance(obj, ActionEvent):
        return obj.__repr__()
    raise TypeError(f"Type {type(obj).__name__} is not serializable")

class Player():

    def __init__(self, username: str, ws: WebSocket | None, position: str, host: bool = False):
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
        elif player.ws is None:
            return {
                "position": player.position,
                "type": "ai",
                "username": player.username,
                "host": False,
                "you": False
            }
        return {
            "position": player.position,
            "type": "human",
            "username": player.username,
            "host": player.host,
            "you": player.username == you
        }

    def is_human(self):
        return self.ws is not None
    
    async def send(self, data):
        if self.is_human():
            await self.ws.send_text(json.dumps(data, default=custom_serializer))

bot_names = [
  "awesom-o-4000",
  "i-robot",
  "gary rollsbot"
]