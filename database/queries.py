def get_max_row_id_of_the_table_query(table: str) -> str:
    """
    """

    return f'''
    SELECT id FROM {table}
    ORDER BY id DESC
    LIMIT 1;
    '''

def insert_into_projects_query() -> str:
    """
    """
    
    return f'''
    INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    '''