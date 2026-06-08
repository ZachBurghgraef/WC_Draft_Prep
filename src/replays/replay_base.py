from enum import Enum, auto
import csv
import re

class replay_player():
    def __init__(self, playerName:str, pokemonTaken:list[str],):
        self.name = playerName
        self.pokemon = pokemonTaken
        self._kills = {}
        self._deaths = []
        self._nicknames = {}

    def pokemon_died(self, pokemon:str):
        if pokemon in self._deaths:
            raise Exception("Pokemon died twice without reviving")
        self._deaths.append(pokemon)

    def attribute_kill(self, pokemon_kill:str, pokemon_killed:str):
        if pokemon_kill not in self._kills:
            self._kills[pokemon_kill] = [pokemon_killed]
        else:
            self._kills[pokemon_kill].append(pokemon_killed)
    
    def get_name_from_nickname(self, nickname:str) -> str:
        if self._names_to_nicknames is None:
            raise Exception("Names-to-Nicknames not set")
        return self._nicknames_to_names[nickname]
    
    def get_nickname_from_name(self, name:str) -> str:
        if self._nicknames_to_names is None:
            raise Exception("Nicknames-to-Names not set")
        return self._names_to_nicknames[name]
    
    def set_nicknames_to_names(self, nicknameDict:dict):
        self._nicknames_to_names = nicknameDict
    def set_names_to_nicknames(self, nicknameDict:dict):
        self._names_to_nicknames = nicknameDict

    def __str__(self) -> str:
        playerPrint = f"\nPlayer: {self.name}\nPokemon Taken: {self.pokemon}\n"
        
        if self._kills != {} or self._deaths != []:
            playerPrint += "Individual Efforts:\n"
            for pokemon in self.pokemon:
                KDs = 0
                playerPrint += f"   {pokemon} -"
                
                if pokemon in self._kills:
                    playerPrint += f"\tKills: {self._kills[pokemon]}"
                    KDs += len(self._kills[pokemon])
                
                if pokemon in self._deaths:
                    playerPrint += f"\tFainted"
                    KDs -= 1
                
                if KDs > 0:
                    playerPrint += f"\t- KD: +{KDs}"
                else:
                    playerPrint += f"\t- KD: {KDs}"
                
                playerPrint += "\n"

        return playerPrint


class replay_types(Enum):
    HTML = auto()


class replay():
    def __init__(self, replayDir:str = "",):
        self.replayDir = replayDir
        self._player1 = None
        self._player2 = None
        self._format = None
        self._log = None
        self.winner = None
        
        fileType = replayDir.split(".")[-1]
        match fileType:
            case r"html":
                self.replay_type = replay_types.HTML
                self.__parse_HTML()
            case _:
                raise Exception(f"Unsupported replay file type: {fileType}")

    def get_players(self):
        return (self._player1, self._player2)
    def get_format(self):
        return (self._format)
    
    def __str__(self):
        return_str = ""
        if self._format:
            return_str += self._format
        if self._player1:
            return_str += str(self._player1)
        if self._player2:
            return_str += str(self._player2)
        return return_str

    def _get_pokemon_kills(self, pokemon_nickname:str) ->list[dict]: #returns in nicknames
        """
        Find all kills (faints in same turn as move) by a given Pokémon in battle log text.
        
        Args:
            text: The battle log text
            pokemon_name: The Pokémon's name/nickname to track (e.g., "p1a: Misty")
        
        Returns:
            List of tuples containing (turn_number, opponent, move_used)
        """
        kills = []
        
        # Split text into turns for easier processing
        if self._log:
            turns = re.split(r'\|turn\|', self._log)
        else:
            raise Exception("Log has not yet been recorded")

        for turn_block in turns[1:]:  # Skip the first split (before any turn marker)
            lines = turn_block.strip().split('\n')
            turn_num = lines[0] if lines else None
            
            # Track moves and faints within this turn
            current_move = None
            current_actor = None
            
            for line in lines[1:]:
                # Parse move lines
                move_match = re.match(r'\|move\|(?:p[12]a): ([^|]+)\|([^|]+)\|([^|]+)', line)
                if move_match:
                    current_actor = move_match.group(1)
                    current_move = move_match.group(2)
                
                # Parse faint lines
                faint_match = re.match(r'\|faint\|(?:p[12]a): ([^|]+)', line)
                if faint_match:
                    fainted_pokemon = faint_match.group(1)
                    # Check if the actor of the last move was our target pokemon and our target pokemon was not the one who died
                    if current_actor == pokemon_nickname and current_move and fainted_pokemon != current_actor:
                        kills.append({
                            'turn': turn_num,
                            'killed': fainted_pokemon,
                            'move': current_move
                        })
    
        return kills

    def __parse_HTML(self):
        filepath = self.replayDir
        
        # read file
        with open(filepath, "r") as file:
            content = file.read()

        # key word match the title of the html downloaded from pokemon showdown to extract players and format
        match = re.search(r'<title>(.*?) replay: (\w+) vs\. (\w+)</title>', content)
        if match:
            self._format = match.group(1)
            player1Name = match.group(2)
            player2Name = match.group(3)

        # find pokemon brought by each player
        match_p1 = re.findall(r"\|poke\|p1\|(.*?)(?:, [M,F])?\|", content)
        match_p2 = re.findall(r"\|poke\|p2\|(.*?)(?:, [M,F])?\|", content)
        
        # make player classes
        self._player1 = replay_player(player1Name, match_p1)
        self._player2 = replay_player(player2Name, match_p2)

        # get log
        match_log = re.search(r'\|start\n(.*?)\|win\|', content, re.DOTALL)
        if match_log:
            self._log = match_log[0] # grabbing the full match

        #### set nicknames
        for player in [(self._player1, "p1a"), (self._player2, "p2a")]:
            # player 1
            playerNicknamesToNames = {}
            playerNamesToNicknames = {}
            for pokemon in player[0].pokemon:
                matches = re.findall(r"\|switch\|" + player[1] + r": (.*?)\|" + pokemon + r"(?:, [MF])?\|", content)
                nickname = pokemon
                if matches != []:
                    nickname = matches[0]
                playerNamesToNicknames[pokemon] = nickname
                playerNicknamesToNames[nickname] = pokemon
            player[0].set_names_to_nicknames(playerNamesToNicknames)
            player[0].set_nicknames_to_names(playerNicknamesToNames)


        # fill out kills and deaths
        players = [self._player1, self._player2]
        for i, player in enumerate(players):
             
            for pokemon in player.pokemon:
                # record fainted pokemon
                if re.search(r"\|faint\|" + f"p{i+1}a" + r": " + player.get_nickname_from_name(pokemon), content):
                    player.pokemon_died(pokemon=pokemon)
    
                # record kills
                print("pokemon kills1: ", len(self._get_pokemon_kills(player.get_nickname_from_name(pokemon))))
                print("pokemon kills2: ", player.get_nickname_from_name(pokemon))

                kill_list = [players[(i+1)%2].get_name_from_nickname(k["killed"]) for k in self._get_pokemon_kills(player.get_nickname_from_name(pokemon))]

                # record only the pokemon killed right now
                print(len(kill_list))
                for kill in kill_list:
                    print(f"{pokemon} killed {kill}")
                    player.attribute_kill(pokemon, kill)

                

