from enum import Enum, auto
import csv
import re

class replay_player():
    def __init__(self, playerName:str, pokemonTaken:list[str],):
        self.name = playerName
        self.pokemon = pokemonTaken
        self._kills = {}
        self._deaths = []

    def pokemon_died(self, pokemon:str):
        if pokemon in self._deaths:
            raise Exception("Pokemon died twice without reviving")
        self._deaths.append(pokemon)

    def attribute_kill(self, pokemon_kill:str, pokemon_killed:str):
        if pokemon_kill not in self._kills:
            self._kills[pokemon_kill] = [pokemon_killed]
        else:
            self._kills[pokemon_kill].append(pokemon_killed)

    def __str__(self):
        playerPrint = f"\nPlayer: {self.name}\nPokemon Taken: {self.pokemon}\n"
        
        if self._kills != {} and self._deaths != []:
            playerPrint += "Individual Efforts:\n"
            for pokemon in self.pokemon:
                KDs = 0
                playerPrint += f"   {pokemon} -"
                
                if pokemon in self._kills:
                    playerPrint += f" Kills: {self._kills[pokemon]}"
                    KDs += 1
                
                if pokemon in self._deaths:
                    playerPrint += f" Fainted"
                    KDs -= 1
                
                if KDs > 0:
                    playerPrint += f" - KD: +{KDs}"
                else:
                    playerPrint += f" - KD: {KDs}"
                
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

    def __parse_HTML(self):
        filepath = r"./data/replays/" + self.replayDir
        
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
        
        self._player1 = replay_player(player1Name, match_p1)
        self._player2 = replay_player(player2Name, match_p2)
