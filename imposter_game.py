import discord
import json
import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum

class GameState(Enum):
    WAITING = "waiting"
    STARTING = "starting"
    DISCUSSION = "discussion"
    VOTING = "voting"
    RESULTS = "results"
    ENDED = "ended"

@dataclass
class Player:
    user_id: int
    username: str
    character: str
    theme: str
    is_imposter: bool
    is_alive: bool = True
    has_spoken: bool = False
    votes_received: int = 0
    
    def to_dict(self):
        return asdict(self)

@dataclass
class GameSession:
    channel_id: int
    host_id: int
    players: Dict[int, Player]
    state: GameState
    round_number: int
    imposters: List[int]
    main_theme: str
    imposter_theme: str
    start_time: datetime
    phase_end_time: Optional[datetime] = None
    eliminated_players: List[int] = None
    chosen_genre: str = "random"
    chosen_subgenre: Optional[str] = None
    min_players: int = 4
    
    def __post_init__(self):
        if self.eliminated_players is None:
            self.eliminated_players = []
    
    def to_dict(self):
        data = asdict(self)
        data['start_time'] = self.start_time.isoformat()
        if self.phase_end_time:
            data['phase_end_time'] = self.phase_end_time.isoformat()
        data['state'] = self.state.value  # Convert enum to string
        return data

class ThemeGenerator:
    def __init__(self):
        self.genres = [
            "Movies", "TV Shows", "Superheroes", "Fantasy", "Sci-Fi", 
            "Anime", "Video Games", "Disney", "Animals", "Food",
            "Countries", "Sports", "Music", "History", "Mythology"
        ]
        # Import here to avoid circular imports
        from ai_handler import _call_openrouter
        self._call_openrouter = _call_openrouter
    
    def get_random_theme_pair(self, genre="random", subgenre=None):
        """Generate a theme pair using AI based on chosen genre and optional subgenre"""
        if genre == "random":
            genre = random.choice(self.genres)
        
        # AI prompt to generate similar but different themes
        system_prompt = """You are a game designer creating themes for an imposter game. 
        Generate 2 similar themes that could be confused but are different enough to create interesting gameplay.
        
        Return ONLY a JSON object with this exact structure:
        {
          "main": "Theme Name",
          "imposter": "Similar Theme Name", 
          "main_chars": ["Character1", "Character2", "Character3", "Character4"],
          "imposter_chars": ["Character1", "Character2", "Character3", "Character4"],
          "main_facts": ["Fact1", "Fact2", "Fact3", "Fact4"],
          "imposter_facts": ["Fact1", "Fact2", "Fact3", "Fact4"],
          "blend_hints": ["How imposter can blend their theme into the main theme"]
        }
        
        Make facts simple and visual. Characters should be recognizable. Blend hints should be creative."""
        
        # Build the prompt based on genre and subgenre
        if subgenre:
            user_prompt = f"""Generate 2 similar {subgenre} themes for an imposter game.
            
            Main Category: {genre}
            Specific Type: {subgenre}
            
            Examples:
            - Disney Movies: "Frozen" vs "Moana" (both Disney princess movies)
            - Horror Movies: "Friday the 13th" vs "Halloween" (both slasher films)
            - Action Movies: "Fast & Furious" vs "Mission Impossible" (both action franchises)
            - Marvel Heroes: "Avengers" vs "X-Men" (both Marvel teams)
            - Fantasy Books: "Harry Potter" vs "Lord of the Rings" (both fantasy magic)
            
            The themes should be:
            1. Both from the {subgenre} category
            2. Similar enough that imposters can blend in
            3. Different enough to create interesting gameplay
            4. Simple enough for all players to understand
            5. Popular enough that most people know them
            
            Create themes specifically for: {subgenre}"""
        else:
            user_prompt = f"""Generate 2 similar {genre} themes for an imposter game.
            
            Examples:
            - Movies: "Frozen" vs "Moana" (both Disney princess movies)
            - Superheroes: "Marvel" vs "DC" (both superhero universes)
            - Fantasy: "Harry Potter" vs "Lord of the Rings" (both fantasy magic)
            
            The themes should be:
            1. Similar enough that imposters can blend in
            2. Different enough to create interesting gameplay
            3. Simple enough for all players to understand
            4. Popular enough that most people know them
            
            Genre: {genre}"""
        
        try:
            response = self._call_openrouter(
                "google/gemini-2.5-flash-preview-05-20",
                system_prompt,
                user_prompt
            )
            
            # Parse JSON response
            import json
            theme_data = json.loads(response.strip())
            
            # Validate structure
            required_keys = ["main", "imposter", "main_chars", "imposter_chars", "main_facts", "imposter_facts", "blend_hints"]
            if all(key in theme_data for key in required_keys):
                return theme_data
            else:
                # Fallback to default if AI response is malformed
                return self.get_fallback_theme()
                
        except Exception as e:
            print(f"AI theme generation failed: {e}")
            return self.get_fallback_theme()
    
    def get_fallback_theme(self):
        """Fallback theme if AI fails"""
        fallback_themes = [
            {
                "main": "Disney Princesses",
                "imposter": "Pixar Characters",
                "main_chars": ["Elsa", "Belle", "Ariel", "Jasmine"],
                "imposter_chars": ["Merida", "Joy", "Dory", "Violet"],
                "main_facts": ["Lives in castle", "Has magic powers", "Sings songs", "Wears pretty dress"],
                "imposter_facts": ["Goes on adventure", "Has special ability", "Helps friends", "Saves the day"],
                "blend_hints": ["Talk about magic, adventures, friends - mention 'princess adventures' and 'magical friends'"]
            },
            {
                "main": "Cats",
                "imposter": "Dogs",
                "main_chars": ["Fluffy", "Whiskers", "Mittens", "Shadow"],
                "imposter_chars": ["Buddy", "Max", "Bella", "Charlie"],
                "main_facts": ["Climbs trees", "Purrs when happy", "Likes fish", "Sleeps in sunny spots"],
                "imposter_facts": ["Fetches sticks", "Wags tail", "Likes bones", "Guards the house"],
                "blend_hints": ["Talk about pets, playing, sleeping - mention 'climbing' and 'fish bones'"]
            }
        ]
        return random.choice(fallback_themes)
    
    def generate_character_card(self, theme_data: dict, is_imposter: bool, character_name: str) -> dict:
        if is_imposter:
            return {
                "title": f"🎭 YOU ARE THE IMPOSTER!",
                "real_theme": theme_data["main"],
                "your_theme": theme_data["imposter"], 
                "character": character_name,
                "your_facts": random.sample(theme_data["imposter_facts"], 3),
                "blend_hints": theme_data["blend_hints"],
                "mission": f"🎯 PRETEND you're from {theme_data['main']}!\n💡 {theme_data['blend_hints'][0]}"
            }
        else:
            return {
                "title": f"🎬 You are from {theme_data['main']}",
                "character": character_name,
                "your_facts": random.sample(theme_data["main_facts"], 3),
                "hint": f"💡 Talk about your character - but don't say '{theme_data['main']}' or '{character_name}'!"
            }

class ImposterGameManager:
    def __init__(self, bot):
        self.bot = bot
        self.games: Dict[int, GameSession] = {}
        self.theme_generator = ThemeGenerator()
        self.data_file = "imposter_games.json"
        self.load_games()
        
    def load_games(self):
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                for channel_id, game_data in data.items():
                    game_data['start_time'] = datetime.fromisoformat(game_data['start_time'])
                    if game_data.get('phase_end_time'):
                        game_data['phase_end_time'] = datetime.fromisoformat(game_data['phase_end_time'])
                    game_data['state'] = GameState(game_data['state'])
                    
                    players = {}
                    for user_id, player_data in game_data['players'].items():
                        players[int(user_id)] = Player(**player_data)
                    game_data['players'] = players
                    
                    # Handle missing fields for backward compatibility
                    if 'chosen_genre' not in game_data:
                        game_data['chosen_genre'] = 'random'
                    if 'chosen_subgenre' not in game_data:
                        game_data['chosen_subgenre'] = None
                    if 'min_players' not in game_data:
                        game_data['min_players'] = 4
                    
                    self.games[int(channel_id)] = GameSession(**game_data)
        except FileNotFoundError:
            pass
    
    def save_games(self):
        data = {}
        for channel_id, game in self.games.items():
            data[str(channel_id)] = game.to_dict()
        
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    async def create_game(self, channel_id: int, host_id: int) -> bool:
        if channel_id in self.games:
            return False
        
        self.games[channel_id] = GameSession(
            channel_id=channel_id,
            host_id=host_id,
            players={},
            state=GameState.WAITING,
            round_number=1,
            imposters=[],
            main_theme="",
            imposter_theme="",
            start_time=datetime.now()
        )
        self.save_games()
        return True
    
    async def join_game(self, channel_id: int, user_id: int, username: str) -> bool:
        if channel_id not in self.games:
            return False
        
        game = self.games[channel_id]
        if game.state != GameState.WAITING:
            return False
        
        if len(game.players) >= 10:  # Max 10 players
            return False
        
        if user_id not in game.players:
            game.players[user_id] = Player(
                user_id=user_id,
                username=username,
                character="",
                theme="",
                is_imposter=False
            )
            self.save_games()
            return True
        return False
    
    async def leave_game(self, channel_id: int, user_id: int) -> bool:
        if channel_id not in self.games:
            return False
        
        game = self.games[channel_id]
        if game.state != GameState.WAITING:
            return False
        
        if user_id in game.players:
            del game.players[user_id]
            self.save_games()
            return True
        return False
    
    async def start_game(self, channel_id: int, host_id: int) -> bool:
        if channel_id not in self.games:
            return False
        
        game = self.games[channel_id]
        if game.host_id != host_id or game.state != GameState.WAITING:
            return False
        
        min_players_required = getattr(game, 'min_players', 4)
        if len(game.players) < min_players_required:
            return False
        
        # Generate theme and assign roles using chosen genre and subgenre
        chosen_genre = getattr(game, 'chosen_genre', 'random')
        chosen_subgenre = getattr(game, 'chosen_subgenre', None)
        theme_data = self.theme_generator.get_random_theme_pair(chosen_genre, chosen_subgenre)
        game.main_theme = theme_data["main"]
        game.imposter_theme = theme_data["imposter"]
        
        # Assign imposters (1 for 4-6 players, 2 for 7+ players)
        num_imposters = 1 if len(game.players) <= 6 else 2
        player_ids = list(game.players.keys())
        game.imposters = random.sample(player_ids, num_imposters)
        
        # Assign characters to players
        main_chars = theme_data["main_chars"] * 3  # Ensure enough characters
        imposter_chars = theme_data["imposter_chars"] * 3
        
        for user_id, player in game.players.items():
            if user_id in game.imposters:
                player.is_imposter = True
                player.character = random.choice(imposter_chars)
                player.theme = theme_data["imposter"]
                imposter_chars.remove(player.character)
            else:
                player.is_imposter = False
                player.character = random.choice(main_chars)
                player.theme = theme_data["main"]
                main_chars.remove(player.character)
        
        game.state = GameState.STARTING
        self.save_games()
        
        # Send character cards to players
        for user_id, player in game.players.items():
            await self.send_character_card(user_id, theme_data, player)
        
        # Start discussion phase after brief delay
        await asyncio.sleep(10)
        await self.start_discussion_phase(channel_id)
        
        return True
    
    async def send_character_card(self, user_id: int, theme_data: dict, player: Player):
        user = self.bot.get_user(user_id)
        if not user:
            return
        
        card = self.theme_generator.generate_character_card(theme_data, player.is_imposter, player.character)
        
        embed = discord.Embed(
            title=card["title"],
            color=discord.Color.red() if player.is_imposter else discord.Color.blue()
        )
        
        if player.is_imposter:
            embed.add_field(name="🎭 Your Character", value=player.character, inline=False)
            embed.add_field(name="🎬 Your Theme", value=card["your_theme"], inline=False)
            embed.add_field(name="📝 Your Facts", value="\n".join(f"• {fact}" for fact in card["your_facts"]), inline=False)
            embed.add_field(name="🎯 Mission", value=card["mission"], inline=False)
            embed.add_field(name="⚠️ Everyone else is from", value=card["real_theme"], inline=False)
        else:
            embed.add_field(name="🎭 Your Character", value=player.character, inline=False)
            embed.add_field(name="📝 Your Facts", value="\n".join(f"• {fact}" for fact in card["your_facts"]), inline=False)
            embed.add_field(name="💡 Hint", value=card["hint"], inline=False)
        
        try:
            await user.send(embed=embed)
        except discord.Forbidden:
            pass
    
    async def start_discussion_phase(self, channel_id: int):
        if channel_id not in self.games:
            return
        
        game = self.games[channel_id]
        game.state = GameState.DISCUSSION
        game.phase_end_time = datetime.now() + timedelta(minutes=4)  # 4 minute discussion
        self.save_games()
        
        channel = self.bot.get_channel(channel_id)
        if channel:
            embed = discord.Embed(
                title="🎭 Discussion Phase Started!",
                description=f"**Theme:** {game.main_theme}\n\n"
                           f"💬 **Talk about your character for 4 minutes!**\n"
                           f"• Share facts about your character\n"
                           f"• Don't say character names directly\n"
                           f"• Try to spot the imposter(s)!\n\n"
                           f"⏰ **Time remaining:** 4:00",
                color=discord.Color.blue()
            )
            await channel.send(embed=embed)
        
        # Start timer task
        asyncio.create_task(self.discussion_timer(channel_id))
    
    async def discussion_timer(self, channel_id: int):
        game = self.games.get(channel_id)
        if not game:
            return
        
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return
        
        # Update timer every 30 seconds
        while game.state == GameState.DISCUSSION and game.phase_end_time > datetime.now():
            remaining = game.phase_end_time - datetime.now()
            minutes = int(remaining.total_seconds() // 60)
            seconds = int(remaining.total_seconds() % 60)
            
            if minutes == 1 and seconds == 0:
                await channel.send("⏰ **1 minute remaining!**")
            elif minutes == 0 and seconds == 30:
                await channel.send("⏰ **30 seconds remaining!**")
            
            await asyncio.sleep(30)
        
        if game.state == GameState.DISCUSSION:
            await self.start_voting_phase(channel_id)
    
    async def start_voting_phase(self, channel_id: int):
        if channel_id not in self.games:
            return
        
        game = self.games[channel_id]
        game.state = GameState.VOTING
        game.phase_end_time = datetime.now() + timedelta(minutes=2)  # 2 minute voting
        
        # Reset votes
        for player in game.players.values():
            player.votes_received = 0
        
        self.save_games()
        
        channel = self.bot.get_channel(channel_id)
        if channel:
            alive_players = [p for p in game.players.values() if p.is_alive]
            player_list = "\n".join([f"{i+1}️⃣ {player.username}" for i, player in enumerate(alive_players)])
            
            embed = discord.Embed(
                title="🗳️ Voting Phase Started!",
                description=f"**Vote who you think is the imposter!**\n\n"
                           f"**Players:**\n{player_list}\n\n"
                           f"React with the number to vote!\n"
                           f"⏰ **Time remaining:** 2:00",
                color=discord.Color.orange()
            )
            
            message = await channel.send(embed=embed)
            
            # Add reaction options
            number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
            for i in range(len(alive_players)):
                await message.add_reaction(number_emojis[i])
            
            # Start voting timer
            asyncio.create_task(self.voting_timer(channel_id))
    
    async def voting_timer(self, channel_id: int):
        game = self.games.get(channel_id)
        if not game:
            return
        
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return
        
        # Wait for voting to complete
        while game.state == GameState.VOTING and game.phase_end_time > datetime.now():
            remaining = game.phase_end_time - datetime.now()
            if remaining.total_seconds() <= 30:
                await channel.send("⏰ **30 seconds remaining to vote!**")
                break
            await asyncio.sleep(30)
        
        await asyncio.sleep(30)  # Wait for final 30 seconds
        
        if game.state == GameState.VOTING:
            await self.end_voting_phase(channel_id)
    
    async def process_vote(self, channel_id: int, user_id: int, vote_index: int) -> bool:
        if channel_id not in self.games:
            return False
        
        game = self.games[channel_id]
        if game.state != GameState.VOTING or user_id not in game.players:
            return False
        
        if not game.players[user_id].is_alive:
            return False
        
        alive_players = [p for p in game.players.values() if p.is_alive]
        if vote_index >= len(alive_players):
            return False
        
        # Count the vote
        target_player = alive_players[vote_index]
        target_player.votes_received += 1
        self.save_games()
        return True
    
    async def end_voting_phase(self, channel_id: int):
        if channel_id not in self.games:
            return
        
        game = self.games[channel_id]
        game.state = GameState.RESULTS
        
        # Find player with most votes
        alive_players = [p for p in game.players.values() if p.is_alive]
        if not alive_players:
            return
        
        most_voted = max(alive_players, key=lambda p: p.votes_received)
        
        # Eliminate the player
        most_voted.is_alive = False
        game.eliminated_players.append(most_voted.user_id)
        
        channel = self.bot.get_channel(channel_id)
        if channel:
            embed = discord.Embed(
                title="🗳️ Voting Results",
                description=f"**{most_voted.username}** was eliminated!\n\n"
                           f"**Votes received:** {most_voted.votes_received}\n"
                           f"**Character:** {most_voted.character}\n"
                           f"**Theme:** {most_voted.theme}\n"
                           f"**Was imposter:** {'Yes! 🎭' if most_voted.is_imposter else 'No! 😇'}",
                color=discord.Color.red() if most_voted.is_imposter else discord.Color.green()
            )
            await channel.send(embed=embed)
        
        # Check win conditions
        await asyncio.sleep(5)
        await self.check_win_conditions(channel_id)
        
        self.save_games()
    
    async def check_win_conditions(self, channel_id: int):
        if channel_id not in self.games:
            return
        
        game = self.games[channel_id]
        alive_players = [p for p in game.players.values() if p.is_alive]
        alive_imposters = [p for p in alive_players if p.is_imposter]
        alive_innocents = [p for p in alive_players if not p.is_imposter]
        
        channel = self.bot.get_channel(channel_id)
        
        if len(alive_imposters) == 0:
            # Innocents win
            game.state = GameState.ENDED
            if channel:
                embed = discord.Embed(
                    title="🎉 Innocents Win!",
                    description="All imposters have been eliminated!\n\n"
                               f"**Imposters were:**\n" + 
                               "\n".join([f"• {game.players[imp_id].username} ({game.players[imp_id].character})" 
                                        for imp_id in game.imposters]),
                    color=discord.Color.green()
                )
                await channel.send(embed=embed)
        elif len(alive_imposters) >= len(alive_innocents):
            # Imposters win
            game.state = GameState.ENDED
            if channel:
                embed = discord.Embed(
                    title="🎭 Imposters Win!",
                    description="Imposters equal or outnumber the innocents!\n\n"
                               f"**Imposters were:**\n" + 
                               "\n".join([f"• {game.players[imp_id].username} ({game.players[imp_id].character})" 
                                        for imp_id in game.imposters]),
                    color=discord.Color.red()
                )
                await channel.send(embed=embed)
        else:
            # Continue to next round
            await asyncio.sleep(3)
            await self.start_discussion_phase(channel_id)
            return
        
        # Game ended, clean up
        await asyncio.sleep(10)
        del self.games[channel_id]
        self.save_games()
    
    def get_game_status(self, channel_id: int) -> Optional[dict]:
        if channel_id not in self.games:
            return None
        
        game = self.games[channel_id]
        alive_players = [p for p in game.players.values() if p.is_alive]
        
        return {
            "state": game.state.value,
            "players": len(game.players),
            "alive_players": len(alive_players),
            "theme": game.main_theme,
            "round": game.round_number,
            "imposters": len(game.imposters)
        }