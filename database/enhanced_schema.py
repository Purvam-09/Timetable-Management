"""
Enhanced Database Schema for Real-World Timetable
Adds: Rooms, Batches, Online Classes
"""

from database.db_setup import get_connection

def add_enhanced_tables():
    """Add new tables for enhanced features"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Rooms/Labs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT NOT NULL UNIQUE,
            room_type TEXT DEFAULT 'classroom',
            capacity INTEGER,
            building TEXT,
            floor INTEGER,
            is_lab INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Class Batches Table (for lab divisions)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS class_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT NOT NULL,
            batch_number INTEGER NOT NULL,
            batch_label TEXT,
            student_count INTEGER,
            semester INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(class_name, batch_number, semester)
        )
    ''')
    
    # 3. Enhanced subject table - add room and online flags
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subject_metadata (
            subject_id INTEGER PRIMARY KEY,
            is_online INTEGER DEFAULT 0,
            preferred_room_id INTEGER,
            requires_lab INTEGER DEFAULT 0,
            batch_division_required INTEGER DEFAULT 0,
            num_batches INTEGER DEFAULT 1,
            FOREIGN KEY (subject_id) REFERENCES subject(id),
            FOREIGN KEY (preferred_room_id) REFERENCES rooms(id)
        )
    ''')
    
    # 4. Enhanced timetable_slots - add room and batch info
    # First check if columns exist
    cursor.execute("PRAGMA table_info(timetable_slots)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'room_id' not in columns:
        cursor.execute('ALTER TABLE timetable_slots ADD COLUMN room_id INTEGER')
    
    if 'batch_id' not in columns:
        cursor.execute('ALTER TABLE timetable_slots ADD COLUMN batch_id INTEGER')
    
    if 'is_online' not in columns:
        cursor.execute('ALTER TABLE timetable_slots ADD COLUMN is_online INTEGER DEFAULT 0')
    
    conn.commit()
    conn.close()
    print("✅ Enhanced schema added successfully!")

def insert_sample_rooms():
    """Insert sample rooms matching your PDF"""
    conn = get_connection()
    cursor = conn.cursor()
    
    rooms = [
        # Classrooms
        ('1NB002', 'classroom', 60, 'NB', 1, 0),
        ('1NB003', 'classroom', 60, 'NB', 1, 0),
        ('1NB102', 'classroom', 60, 'NB', 1, 0),
        ('1NB108', 'classroom', 60, 'NB', 1, 0),
        ('1NB109', 'classroom', 60, 'NB', 1, 0),
        ('1NB210', 'classroom', 60, 'NB', 2, 0),
        ('2NB004', 'classroom', 60, 'NB', 2, 0),
        ('2NB209', 'classroom', 60, 'NB', 2, 0),
        
        # Labs
        ('1NB004B', 'lab', 30, 'NB', 1, 1),
        ('1NB004C', 'lab', 30, 'NB', 1, 1),
        ('1NB005A', 'lab', 30, 'NB', 1, 1),
        ('1NB005B', 'lab', 30, 'NB', 1, 1),
        ('1NB011', 'lab', 30, 'NB', 1, 1),
        ('1NB012', 'lab', 30, 'NB', 1, 1),
        ('1NB013', 'lab', 30, 'NB', 1, 1),
        ('1NB014', 'lab', 30, 'NB', 1, 1),
        ('1NB015', 'lab', 30, 'NB', 1, 1),
        ('1NB016', 'lab', 30, 'NB', 1, 1),
        ('1NB104C', 'lab', 30, 'NB', 1, 1),
        ('1NB105B', 'lab', 30, 'NB', 1, 1),
        ('1NB106A', 'lab', 30, 'NB', 1, 1),
        ('1NB106B', 'lab', 30, 'NB', 1, 1),
        ('1NB106C', 'lab', 30, 'NB', 1, 1),
        ('1NB110A', 'lab', 30, 'NB', 1, 1),
        ('1NB110B', 'lab', 30, 'NB', 1, 1),
        ('1NB110C', 'lab', 30, 'NB', 1, 1),
        ('1NB111A', 'lab', 30, 'NB', 1, 1),
        ('1NB111B', 'lab', 30, 'NB', 1, 1),
        ('1NB111C', 'lab', 30, 'NB', 1, 1),
        ('1NB112A', 'lab', 30, 'NB', 1, 1),
        ('1NB112B', 'lab', 30, 'NB', 1, 1),
        ('1NB112C', 'lab', 30, 'NB', 1, 1),
        ('1NBPGSEM', 'lab', 30, 'NB', 1, 1),
        
        # Online (virtual)
        ('Online', 'online', 999, 'Virtual', 0, 0),
    ]
    
    try:
        for room in rooms:
            cursor.execute('''
                INSERT OR IGNORE INTO rooms (room_number, room_type, capacity, building, floor, is_lab)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', room)
        
        conn.commit()
        print(f"✅ Inserted {len(rooms)} rooms")
    except Exception as e:
        print(f"❌ Error inserting rooms: {e}")
    finally:
        conn.close()

def create_class_batches(class_name, semester, num_batches=3):
    """Create batch divisions for a class (for labs)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        for i in range(1, num_batches + 1):
            cursor.execute('''
                INSERT OR IGNORE INTO class_batches (class_name, batch_number, batch_label, semester)
                VALUES (?, ?, ?, ?)
            ''', (class_name, i, f"{class_name}-{i}", semester))
        
        conn.commit()
        print(f"✅ Created {num_batches} batches for {class_name}")
    except Exception as e:
        print(f"❌ Error creating batches: {e}")
    finally:
        conn.close()

def get_available_rooms(is_lab=False, exclude_ids=None):
    """Get available rooms for allocation"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM rooms WHERE is_lab = ?'
    params = [1 if is_lab else 0]
    
    if exclude_ids:
        placeholders = ','.join('?' * len(exclude_ids))
        query += f' AND id NOT IN ({placeholders})'
        params.extend(exclude_ids)
    
    cursor.execute(query, params)
    rooms = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return rooms

if __name__ == "__main__":
    print("🔧 Setting up enhanced database...")
    add_enhanced_tables()
    insert_sample_rooms()
    
    # Create sample batches
    create_class_batches('7CE-A', 7, 3)
    create_class_batches('7CE-B', 7, 2)
    create_class_batches('7IT-A', 7, 3)
    create_class_batches('7IT-B', 7, 2)
    
    print("✅ Enhanced database setup complete!")