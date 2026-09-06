import sqlite3
import httpx
import asyncio

def insert_or_get_id(conn: sqlite3.Connection, table: str, name: str, **kwargs) -> int | None:
    """Insert a record if it doesn't exist, and return its ID.
    
    Raises sqlite3.DatabaseError if the operation fails.
    """

    cursor = conn.cursor()
    
    try:
        # Try to get existing ID
        cursor.execute(f"SELECT id FROM {table} WHERE name = ?", (name,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        # Insert new record
        columns = ["name"] + list(kwargs.keys())
        values = [name] + list(kwargs.values())
        placeholders = ", ".join(["?"] * len(columns))
        col_str = ", ".join(columns)
        
        cursor.execute(f"INSERT INTO {table} ({col_str}) VALUES ({placeholders})", values)
        conn.commit()
        
        return cursor.lastrowid
    
    except sqlite3.DatabaseError as e:
        conn.rollback()
        raise ValueError(f"Failed to insert/get {name} in {table}: {e}") from e

async def fetch_pokemon_data(client: httpx.AsyncClient, pokemon_id: int, base_url: str) -> tuple:
    """Fetch pokemon and species data with async"""
    try:
        pokemon_response, species_response = await asyncio.gather(
            client.get(f"{base_url}/pokemon/{pokemon_id}"),
            client.get(f"{base_url}/pokemon-species/{pokemon_id}"),
            return_exceptions=True
        )
        
        # Now you have to check if they're exceptions or responses
        if isinstance(pokemon_response, Exception):
            print(f"Pokemon request failed: {pokemon_response}")
            pokemon_response = None
        else:
            pokemon_response.raise_for_status()
        
        if isinstance(species_response, Exception):
            print(f"Species request failed: {species_response}")
            species_response = None
        else:
            species_response.raise_for_status()
        
        return pokemon_id, pokemon_response.json() if pokemon_response else None, species_response.json() if species_response else None

    except Exception as e:
        print(f"Unexpected error requesting pokemon id:{pokemon_id}\nerror: {e}")
        return pokemon_id, None, None

async def fetch_move_data(client: httpx.AsyncClient, move_url: str) -> dict | None:
    """fetch move details from URL"""
    try:
        response = await client.get(move_url)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        print(f"Error fetching move from {move_url}: {e}")
        return None

async def is_final_evolution(client: httpx.AsyncClient, pokemon_name: str, url: str) -> bool|None:
    try:
        response = await client.get(url)
        response.raise_for_status()
        evo_chain = response.json()
    except httpx.HTTPError as e:
        print(f"Error fetching evolution_chain from {url}: {e}")
        return None

    def branched_tree_search_recursive(name:str, chain:dict):
        # find the right node
        if chain["species"]["name"] == name.lower():
            if len(chain["evolves_to"]) == 0:
                return True
            else:
                return False
        # not the right node, keep looking
        else:
            # end of the branch and didn't find the name
            if len(chain["evolves_to"]) == 0:
                return False
            # return all true if any children return true
            return any([branched_tree_search_recursive(name = name, chain = species) for species in chain["evolves_to"]])
                
    return branched_tree_search_recursive(name = pokemon_name,chain=evo_chain["chain"])

async def process_pokemon(
        conn: sqlite3.Connection,
        pokemon_id: int,
        pokemon_data: dict,
        species_data: dict,
        client: httpx.AsyncClient,
        write_over: bool = False,
                        ) -> bool:
    """get all data and insert data for a pokemon into database"""

    if write_over:
        sql_replace = "REPLACE"
    else:
        sql_replace = "IGNORE"

    try:    # maybe too general of a try-except catch
        cursor = conn.cursor()

        # Extracting Base Stats
        name = pokemon_data['name'].capitalize()
        hp = pokemon_data['stats'][0]['base_stat']
        attack = pokemon_data['stats'][1]['base_stat']
        defense = pokemon_data['stats'][2]['base_stat']
        sp_attack = pokemon_data['stats'][3]['base_stat']
        sp_defense = pokemon_data['stats'][4]['base_stat']
        speed = pokemon_data['stats'][5]['base_stat']

        # Check if fully evolved
        fully_evolved = await is_final_evolution(client= client, url=species_data["evolution_chain"]["url"], pokemon_name=pokemon_data["name"])
        if fully_evolved is None:
            fully_evolved = False

        cursor.execute(f'''
        INSERT OR {sql_replace} INTO pokemon 
        (pokemon_id, name, hp, attack, defense, sp_attack, sp_defense, speed, fully_evolved)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (pokemon_id, name, hp, attack, defense, sp_attack, sp_defense, speed, fully_evolved))
        
        conn.commit()
        
        # Insert Types
        for idx, type_data in enumerate(pokemon_data['types'], 1):
            type_name = type_data['type']['name'].capitalize()
            type_id = insert_or_get_id(conn, "types", type_name)
            
            cursor.execute(f'''
                INSERT OR {sql_replace} INTO pokemon_types (pokemon_id, type_id, slot)
                VALUES (?, ?, ?)
            ''', (pokemon_id, type_id, idx))

            conn.commit()

        # Insert Abilities
        for ability_data in pokemon_data['abilities']:
            ability_name = ability_data['ability']['name'].capitalize()
            is_hidden = ability_data['is_hidden']
            ability_id = insert_or_get_id(conn, "abilities", ability_name)
            
            cursor.execute(f'''
                INSERT OR {sql_replace} INTO pokemon_abilities (pokemon_id, ability_id, is_hidden)
                VALUES (?, ?, ?)
            ''', (pokemon_id, ability_id, is_hidden))
            conn.commit()
        
        # Insert Generation
        generation_name = species_data['generation']['name'].capitalize()
        gen_num = int(species_data['generation']['url'].split('/')[-2])
        generation_id = insert_or_get_id(
            conn, "generations", generation_name, 
            generation_number=gen_num
        )
        
        cursor.execute(f'''
            INSERT OR {sql_replace} INTO pokemon_generations (pokemon_id, generation_id)
            VALUES (?, ?)
        ''', (pokemon_id, generation_id))
        conn.commit()

        # Fetch and insert moves concurrently
        move_urls = [move_data['move']['url'] for move_data in pokemon_data['moves']]
        move_details_list = await asyncio.gather(
            *[fetch_move_data(client, url) for url in move_urls],
            return_exceptions=True
        )
        
        for move_data, move_details in zip(pokemon_data['moves'], move_details_list):
            if not move_details or isinstance(move_details, Exception):
                continue

            try:
                move_name = move_data['move']['name'].capitalize()
                move_type = move_details['type']['name'].capitalize()
                category = move_details['damage_class']['name'].capitalize()
                power = move_details.get('power')
                accuracy = move_details.get('accuracy')
                pp = move_details['pp']
                effect = move_details.get('effect_entries', [{}])[0].get('effect', '') if move_details.get('effect_entries') else ''
                
                # Insert move
                move_id = insert_or_get_id(
                    conn, "moves", move_name,
                    type=move_type, category=category, power=power, 
                    accuracy=accuracy, pp=pp, effect=effect
                )
                
                # Extract learning method and level
                learn_method = None
                learn_level = None
                for version_group_detail in move_data['version_group_details']:
                    learn_method = version_group_detail['move_learn_method']['name']
                    learn_level = version_group_detail.get('level_learned_at')
                    break
                
                # Insert pokemon-move relationship
                cursor.execute(f'''
                    INSERT OR {sql_replace} INTO pokemon_moves 
                    (pokemon_id, move_id, learn_method, learn_level)
                    VALUES (?, ?, ?, ?)
                ''', (pokemon_id, move_id, learn_method, learn_level))
                conn.commit()
            
            except Exception as e:
                print(f"Error processing move for Pokémon {name}: {e}")
                continue
        
        return True
    
    except Exception as e:
        print(f"Error processing Pokémon {pokemon_id}: {e}")
        return False

async def populate_pokedex_async(db_name: str = "pokedex.db", limit: int = 1025, batch_size: int = 50, write_over: bool = False):
    """Async version using concurrent requests with batching."""
    conn = sqlite3.connect(db_name)
    base_url = "https://pokeapi.co/api/v2"
    
    print(f"Populating Pokédex with {limit} Pokémon (async)...")
    
    async with httpx.AsyncClient(timeout=20.0, limits=httpx.Limits(max_connections=20)) as client:
        # Process in batches to avoid overwhelming the API
        for batch_start in range(1, limit + 1, batch_size):
            batch_end = min(batch_start + batch_size, limit + 1)
            batch_ids = range(batch_start, batch_end)
            
            # Fetch all Pokémon data in batch concurrently
            fetch_tasks = [fetch_pokemon_data(client, pokemon_id, base_url) for pokemon_id in batch_ids]
            results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
            
            # Process each Pokémon's data
            process_tasks = []
            for result in results:
                if isinstance(result, Exception):
                    print(f"Error in batch: {result}")
                    continue
                
                pokemon_id, pokemon_data, species_data = result
                if not pokemon_data or not species_data:
                    continue
                
                # Create a task for processing this Pokémon
                process_tasks.append(
                    process_pokemon(conn, pokemon_id, pokemon_data, species_data, client, write_over)
                )
            
            # Process all Pokémon in batch concurrently
            await asyncio.gather(*process_tasks, return_exceptions=True)
            
            print(f"Progress: {min(batch_end - 1, limit)}/{limit}")
    
    conn.close()
    print("Pokédex population complete!")

if __name__ == "__main__":
    asyncio.run(populate_pokedex_async(limit=1025, batch_size=50, write_over=True))