import pandas as pd
import sqlite3

def get_pokedex_table(db_name = "pokedex.db", only_fully_evolved: bool = False, include_moves: bool = False) -> pd.DataFrame:

    db_name = "pokedex.db"
    conn = sqlite3.connect(db_name)

    df = get_stats_table(conn, only_fully_evolved)

    if include_moves:

        moves_df = get_moves_table(conn, only_fully_evolved)
        
        df = pd.merge(df, moves_df, on= "pokemon_name")
    
    return df

def get_stats_table(conn, only_fully_evolved: bool = False) -> pd.DataFrame:
    evolved_filter = " WHERE fully_evolved = true" if only_fully_evolved else ""
    
    query = f"""
        SELECT 
        name AS pokemon_name, 
        hp, 
        attack, 
        defense, 
        sp_attack, 
        sp_defense, 
        speed
        
        FROM pokemon
        {evolved_filter}
        ORDER BY pokemon_id
        """
    return pd.read_sql_query(query, conn)

def get_moves_table(conn, only_fully_evolved: bool = False):
    evolved_filter = " WHERE p.fully_evolved = true" if only_fully_evolved else ""
    query=f"""
        SELECT  
            p.name AS pokemon_name,
            m.name AS move_name
        
        FROM pokemon p
        JOIN pokemon_moves pm ON p.pokemon_id = pm.pokemon_id
        JOIN moves m ON pm.move_id = m.id
        {evolved_filter}
        ORDER BY p.pokemon_id
        """
    pokemon_moves = pd.read_sql_query(query, conn)

    # Label the known learned moves
    pokemon_moves["learns"] = True

    # pivot table so that they can be joined
    pivoted_pokemon_moves = pokemon_moves.pivot_table(
        index=["pokemon_name"],
        columns="move_name",
        values="learns",
        fill_value=False,
        aggfunc='any'
    )

    pivoted_pokemon_moves = pivoted_pokemon_moves.astype(bool)
    pivoted_pokemon_moves = pivoted_pokemon_moves.rename_axis(columns=None)
    pivoted_pokemon_moves = pivoted_pokemon_moves.reset_index()
    return pivoted_pokemon_moves