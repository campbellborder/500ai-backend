import time
import random
from fastapi import (
    WebSocket
)
from classes.player import Player, bot_names
from rlcard.games.five_hundred.game import FiveHundredGame
from rlcard.games.five_hundred.utils.action_event import PassAction, BidAction, PlayCardAction
from rlcard.games.five_hundred.utils.five_hundred_card import FiveHundredCard

async def create_game(gamecode, username, ws):
    game = Game(gamecode, username, ws)
    await game._init()
    return game

class Game:
    
    positions = ["N", "E", "S", "W"]
    orders = {"H": ["H", "C", "D", "S"],
              "D": ["D", "C", "H", "S"],
              "C": ["C", "H", "S", "D"],
              "S": ["S", "H", "C", "D"]}

    def __init__(self, gamecode: str, username: str, ws: WebSocket):
        
        self.gamecode = gamecode
        self.players = [Player(username, ws, Game.positions[0], host=True)]
        self.phase = "setup"
        self._game = FiveHundredGame()
    
    async def _init(self):
        await self._broadcast_state()

    def is_over(self):
        return self._game.is_over()

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

    async def update(self, username, update):
        if update["phase"] == self.phase:
            action = update["action"]
            match action["type"]:
                case "move-position":
                    self._handle_move(username, action["position"])
                case "start-game":
                    self._start_game()
                case "pass":
                    self._handle_pass()
                case "make-bid":
                    self._handle_bid(action["amount"], action["suit"])
                case "play-card":
                    self._handle_card(action["rank"], action["suit"])

        await self._broadcast_state()

    async def ai_update(self):
        """Handle the ai players actions
        """
        if self.phase == "play": 
            current_player = self.players[self._game.get_player_id()]
            while not current_player.is_human():
                legal_actions = self._game.judger.get_legal_actions()
                if self._game.round.round_phase == "bid":
                    if PassAction() in legal_actions:
                        legal_actions = [PassAction(), PassAction(), PassAction(), PassAction(), random.choice(self._game.judger.get_legal_actions())]
                action = random.choice(legal_actions)
                self._game.step(action)

                await self._broadcast_state()
                current_player = self.players[self._game.get_player_id()]
                time.sleep(1)

    async def player_disconnect(self, username):
        """Handle a player disconnecting 
        
            Parameters:
                username (string): The username of the player that disconnected

            Returns:
                The number of human players remaining
        """
        
        # Remove player from list
        player = self._get_player(username)
        position = player.position
        self.players.remove(player)

        # If no human players left, return
        if not self._num_human_players(): 
            return 0

        await self._broadcast_alert("player-left", player.username)

        if player.host:
            # Host has left, define new host
            new_host = next(player for player in self.players if player.is_human()) 
            new_host.host = True
            await self._broadcast_alert("new-host", new_host.username)

        # Add an AI player if during play phase
        if self.phase == "play":
            self.players.append(Player(random.choice(bot_names), None, position))
            self._order_players()

        await self._broadcast_state()
        return self._num_human_players()

    def _get_player(self, username):
        return next(player for player in self.players if player.username == username)

    def _taken_positions(self):
        return [player.position for player in self.players if player.is_human()]

    def game_full(self):
        return len(self._taken_positions()) == len(Game.positions)

    async def _broadcast_state(self):
        for player in self.players:
            if player.is_human():
                await player.send(self._get_state_message(player.username))
    
    async def _broadcast_alert(self, status, username):
        for player in self.players:
            if player.is_human():
                message = {"type": "alert", "status": status, "username": username}
                if status == "new-host":
                    message["you"] = player.username == username
                if status == "player-joined" and player.username == username:
                    continue
                await player.send(message)

    def _handle_card(self, rank, suit):
        card = FiveHundredCard(suit, rank)
        action = PlayCardAction(card)
        self._game.step(action)

    def _handle_bid(self, amount, suit):
        if suit == "M":
            action = BidAction(None, None, misere=True, open=False)
        elif suit == "OM":
            action = BidAction(None, None, misere=True, open=True)
        else:
            action = BidAction(int(amount), suit)
        self._game.step(action)

    def _handle_pass(self):
        action = PassAction()
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

    def _sort_hand(self, hand):
        
        sorted_hand = []
        trump_suit = self._game.round.get_trump_suit()
        order = Game.orders.get(trump_suit, Game.orders["H"])
        joker = next((card for card in hand if card.rank == "RJ"), None)
        if joker:
            sorted_hand.append(joker)
        for suit in order:
            suit_cards = [card for card in hand if card.get_round_suit(trump_suit) == suit]
            suit_cards.sort(key=lambda x: x.get_round_rank(trump_suit), reverse=True)
            sorted_hand += suit_cards
        return sorted_hand
        
        
    def _get_state_message(self, username):
        
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

            if state["round_phase"] in ["discard", "play"]:
                
                message["contract"] = state["contract"].action
                message["trick"] = state["trick_moves"]
                if self._game.round.is_discarding_over():
                  message["lead"] = Game.positions[state["lead"]]

            for i, player in enumerate(message["players"]):
                player["current"] = bool(state["current_player_id"] == i)
                player["num_cards"] = len(state["hands"][i])
                if player["you"]:
                    player["hand"] = self._sort_hand(state["hands"][i])
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

        return message
  