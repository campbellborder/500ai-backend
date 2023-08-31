from utils import get_unique_word
from classes.game import Game, create_game

class GameManager:
    
    def __init__(self):
        self.games = {}

    def game_exists(self, gamecode: str) -> bool:
        return gamecode in self.games
    
    def username_taken(self, gamecode: str, username: str) -> bool:
        game = self.games[gamecode]
        return any(player.username == username for player in game.players)
    
    async def new_game(self, username, ws) -> str:
        gamecode = get_unique_word(self.games.keys())
        game = await create_game(gamecode, username, ws)
        self.games[gamecode] = game
        return gamecode
    
    async def join_game(self, gamecode, username, ws) -> Game:
        game = self.games[gamecode]
        await game.add_player(username, ws)
        return game
    
    async def player_disconnect(self, gamecode, username):
        game = self.games[gamecode]
        await game.player_disconnect(username)
        if game.over:
            del self.games[gamecode]