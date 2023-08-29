from fastapi import (
    WebSocket
)

class Player():

    def __init__(self, username: str, ws: WebSocket):
        self.username = username
        self.ws = ws


class Game:

    def __init__(self, player):

        self.players: list[Player] = [player]
