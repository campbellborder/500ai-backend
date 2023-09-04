import random
from fastapi import (
    WebSocket
)
from classes.player import Player, bot_names
from rlcard.games.five_hundred.game import FiveHundredGame
from rlcard.games.five_hundred.utils.action_event import ActionEvent

async def create_game(gamecode, username, ws):
    game = Game(gamecode, username, ws)
    await game._init()
    return game

class Game:
    
    positions = ["N", "E", "S", "W"]

    def __init__(self, gamecode: str, username: str, ws: WebSocket):
        
        self.gamecode = gamecode
        self.players = [Player(username, ws, Game.positions[0], host=True)]
        self.over = False
        self.phase = "setup"
        self._game = FiveHundredGame()
    
    async def _init(self):
        await self._broadcast_state()

    async def add_player(self, username, ws):

        for position in Game.positions:
            if position not in self._taken_positions():
              player = Player(username, ws, position)
              if self.phase == "play":
                  bot = next(player for player in self.players if not player.is_human())
                  self.players.remove(bot)
              self.players.append(player)
              self._order_players()
              break
        
        await self._broadcast_state()
        await self._broadcast_alert("player-joined", username)

    def _get_player(self, username):
        return next(player for player in self.players if player.username == username)

    def _taken_positions(self):
        return [player.position for player in self.players if player.is_human()]

    def game_full(self):
        return len(self._taken_positions()) == len(Game.positions)

    async def _broadcast_state(self):
        for player in self.players:
            if player.is_human():
                await player.send(self.get_state_message(player.username))
    
    async def _broadcast_alert(self, status, username):
        for player in self.players:
            if player.is_human():
                message = {"type": "alert", "status": status, "username": username}
                if status == "new-host":
                    message["you"] = player.username == username
                if status == "player-joined" and player.username == username:
                    continue
                await player.send(message)

    async def update(self, username, update):
        if update["phase"] == self.phase:
            action = update["action"]
            match action["type"]:
                case "move-position":
                    self._handle_move(username, action["position"])
                case "start-game":
                    self._start_game()
                case "make-bid":
                    self._handle_bid(username, action["bid"])
                case "play-card":
                    self._handle_card(username, action["card"])

        await self._broadcast_state()

    def _handle_bid(self, username, bid):
        action = ActionEvent.from_repr(bid)
        self._game.step(action)
    
    def _handle_move(self, username, position):
        if position not in self._taken_positions():
            self._get_player(username).position = position

    def _start_game(self):
        self.phase = "play"
        self._game.init_game()
        for position in set(Game.positions) - set(self._taken_positions()):
            self.players.append(Player(random.choice(bot_names), None, position))

        self._order_players()

    def _num_human_players(self):
        return sum([player.is_human() for player in self.players])
    
    def _order_players(self):
        self.players.sort(key=lambda player: Game.positions.index(player.position))

    async def player_disconnect(self, username):
        
        player = self._get_player(username)
        position = player.position
        self.players.remove(player)

        if not self._num_human_players(): 
            # Only player has left, destroy game
            self.over = True
            for player in self.players:
                if player.is_human():
                  await player.ws.close()
            return

        await self._broadcast_alert("player-left", player.username)

        if player.host:
            # Host has left, new host
            new_host = next(player for player in self.players if player.is_human())
            new_host.host = True
            await self._broadcast_alert("new-host", new_host.username)

        if self.phase == "play":
            self.players.append(Player(None, None, position))
            self._order_players()

        await self._broadcast_state()
        
    def get_state_message(self, username):
        
        message = {}
        message["type"] = "state"
        message["phase"] = self.phase
        message["gamecode"] = self.gamecode
        message["players"] = [Player.get_state_repr(player, username) for player in self.players]
        
        if self.phase == "setup":
            for position in set(Game.positions) - set(self._taken_positions()):
                message["players"].append(Player.get_state_repr(None, None, position))
            
        elif self.phase == "play":
            state = self._game.get_perfect_information()
            message["round_phase"] = state["round_phase"]
            message["scores"] = state["scores"]

            for i, player in enumerate(message["players"]):
                player["current"] = bool(state["current_player_id"] == i)
                player["num_cards"] = len(state["hands"][i])
                if player["you"]:
                    player["hand"] = state["hands"][i]
                    if player["current"]:
                        player["actions"] = self._game.judger.get_legal_actions()
                
                if state["round_phase"] == "bid":
                    player["bids"] = state["bids"][i]
                    
                elif state["round_phase"] == "discard":
                    # ?
                    pass
                elif state["round_phase"] == "play":
                    # declarers hand if OM and 1 trick been played
                    # ?
                    pass
                else:
                    # over?
                    pass

        print(self.gamecode)
        return message
  