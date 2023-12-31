from utils import get_unique_word
from classes.game import Game, create_game

class GameManager:
    
    def __init__(self):
        self.games = {}

    def game_exists(self, gamecode: str) -> bool:
        return gamecode in self.games
    
    def game_full(self, gamecode: str) -> bool:
        return self.games[gamecode].game_full()
    
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
        num_human_players = await game.player_disconnect(username)
        if num_human_players == 0:
            self.remove_game(gamecode)

    def remove_game(self, gamecode):
        del self.games[gamecode]