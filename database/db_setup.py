# Database initialization

"""
Database Setup and Initialization Module
Creates all necessary tables for the Timetable Management System
"""

import sqlite3
import os

DATABASE_PATH = 'database/timetable.db'

def get_connection():
    """Create and return a database connection"""
    os.makedirs('database', exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

def initialize_database():
    """
    Create all necessary tables for the system
    This should be run once when setting up the project
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Academic Configuration Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS academic_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            academic_year TEXT NOT NULL,
            term TEXT NOT NULL,
            semester INTEGER NOT NULL,
            working_days TEXT NOT NULL,
            shift_mode TEXT NOT NULL,
            shift_timings TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # 2. Faculty Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_name TEXT NOT NULL,
            short_name TEXT NOT NULL UNIQUE,
            specialization TEXT,
            availability TEXT DEFAULT 'Mon,Tue,Wed,Thu,Fri,Sat',
            max_hours_per_week INTEGER DEFAULT 24,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 3. Subject Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subject (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            semester INTEGER NOT NULL,
            lecture_credits INTEGER DEFAULT 0,
            lab_credits INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 4. Faculty-Subject Mapping Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faculty_subject (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            preferred INTEGER DEFAULT 0,
            max_weekly_load INTEGER DEFAULT 6,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id),
            FOREIGN KEY (subject_id) REFERENCES subject(id),
            UNIQUE(faculty_id, subject_id)
        )
    ''')
    
    # 5. Timetable Slots Table (Generated schedules)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS timetable_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            slot_number INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            subject_id INTEGER,
            faculty_id INTEGER,
            slot_type TEXT DEFAULT 'lecture',
            is_break INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (config_id) REFERENCES academic_config(id),
            FOREIGN KEY (subject_id) REFERENCES subject(id),
            FOREIGN KEY (faculty_id) REFERENCES faculty(id)
        )
    ''')
    
    # 6. Upload History Table (Track uploads)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS upload_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_type TEXT NOT NULL,
            filename TEXT NOT NULL,
            records_count INTEGER,
            status TEXT DEFAULT 'success',
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

def reset_database():
    """
    Drop all tables and reinitialize (useful for testing)
    WARNING: This deletes all data!
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    tables = ['timetable_slots', 'faculty_subject', 'subject', 'faculty', 
              'academic_config', 'upload_history']
    
    for table in tables:
        cursor.execute(f'DROP TABLE IF EXISTS {table}')
    
    conn.commit()
    conn.close()
    
    print("🗑️  All tables dropped!")
    initialize_database()

def get_table_info():
    """Display all tables and their row counts (for debugging)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print("\n📊 Database Tables:")
    print("-" * 50)
    
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  {table_name}: {count} records")
    
    conn.close()

if __name__ == "__main__":
    # Run this file directly to initialize the database
    print("🚀 Setting up database...")
    initialize_database()
    get_table_info()
