import sqlite3

def create_pokedex_database(db_name: str = "pokedex.db"):
    """Create and initialize the Pokédex database with normalized schema."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Core Pokemon table (simplified — no repeated fields)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pokemon (
            pokemon_id INTEGER PRIMARY KEY NOT NULL,
            name TEXT UNIQUE NOT NULL,
            hp INTEGER NOT NULL,
            attack INTEGER NOT NULL,
            defense INTEGER NOT NULL,
            sp_attack INTEGER NOT NULL,
            sp_defense INTEGER NOT NULL,
            speed INTEGER NOT NULL,
            fully_evolved BOOLEAN NOT NULL
        )
    ''')
    
    # Types table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS types (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )
    ''')
    
    # Pokemon-Types junction table (many-to-many)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pokemon_types (
            id INTEGER PRIMARY KEY,
            pokemon_id INTEGER NOT NULL,
            type_id INTEGER NOT NULL,
            slot INTEGER NOT NULL,
            FOREIGN KEY (pokemon_id) REFERENCES pokemon(pokemon_id),
            FOREIGN KEY (type_id) REFERENCES types(id),
            UNIQUE(pokemon_id, type_id)
        )
    ''')
    
    # Abilities table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS abilities (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            effect TEXT
        )
    ''')
    
    # Pokemon-Abilities junction table (many-to-many)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pokemon_abilities (
            id INTEGER PRIMARY KEY,
            pokemon_id INTEGER NOT NULL,
            ability_id INTEGER NOT NULL,
            is_hidden BOOLEAN NOT NULL DEFAULT 0,
            FOREIGN KEY (pokemon_id) REFERENCES pokemon(pokemon_id),
            FOREIGN KEY (ability_id) REFERENCES abilities(pokemon_id),
            UNIQUE(pokemon_id, ability_id)
        )
    ''')
    
    # Generations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS generations (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            generation_number INTEGER UNIQUE NOT NULL
        )
    ''')
    
    # Pokemon-Generations junction table (many-to-many)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pokemon_generations (
            id INTEGER PRIMARY KEY,
            pokemon_id INTEGER NOT NULL,
            generation_id INTEGER NOT NULL,
            FOREIGN KEY (pokemon_id) REFERENCES pokemon(pokemon_id),
            FOREIGN KEY (generation_id) REFERENCES generations(id),
            UNIQUE(pokemon_id, generation_id)
        )
    ''')
    
    # Moves table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS moves (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            power INTEGER,
            accuracy INTEGER,
            pp INTEGER NOT NULL,
            effect TEXT
        )
    ''')
    
    # Pokemon-Moves junction table (many-to-many)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pokemon_moves (
            id INTEGER PRIMARY KEY,
            pokemon_id INTEGER NOT NULL,
            move_id INTEGER NOT NULL,
            learn_method TEXT,
            learn_level INTEGER,
            FOREIGN KEY (pokemon_id) REFERENCES pokemon(pokemon_id),
            FOREIGN KEY (move_id) REFERENCES moves(id),
            UNIQUE(pokemon_id, move_id, learn_method, learn_level)
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database '{db_name}' created successfully")

if __name__ == "__main__":
    create_pokedex_database()
