"""
Add this to database/db_setup.py in the initialize_database() function
OR create a new migration file
"""

def add_locations_table():
    """Add locations table to existing database"""
    from database.db_setup import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create locations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT NOT NULL UNIQUE,
            building TEXT DEFAULT 'Main',
            floor INTEGER DEFAULT 0,
            room_type TEXT DEFAULT 'Classroom',
            capacity INTEGER DEFAULT 60,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Locations table created successfully!")

# Run this to add the table
if __name__ == "__main__":
    add_locations_table()