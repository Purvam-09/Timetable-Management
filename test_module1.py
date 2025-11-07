"""
Test Script for Module 1: Database Setup
Run this to verify database creation
"""

import sys
sys.path.append('.')

from database.db_setup import initialize_database, get_connection, get_table_info

def test_database_creation():
    """Test if all tables are created properly"""
    print("=" * 60)
    print("🧪 TESTING MODULE 1: Database Setup")
    print("=" * 60)
    
    # Initialize database
    print("\n1️⃣ Creating database...")
    initialize_database()
    
    # Verify tables exist
    print("\n2️⃣ Verifying tables...")
    conn = get_connection()
    cursor = conn.cursor()
    
    expected_tables = [
        'academic_config',
        'faculty',
        'subject',
        'faculty_subject',
        'timetable_slots',
        'upload_history'
    ]
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    actual_tables = [row[0] for row in cursor.fetchall()]
    
    all_present = all(table in actual_tables for table in expected_tables)
    
    if all_present:
        print("✅ All required tables created successfully!")
    else:
        print("❌ Some tables are missing!")
        missing = set(expected_tables) - set(actual_tables)
        print(f"Missing tables: {missing}")
    
    conn.close()
    
    # Show table info
    print("\n3️⃣ Database Summary:")
    get_table_info()
    
    print("\n" + "=" * 60)
    print("✅ MODULE 1 TEST COMPLETE")
    print("=" * 60)

def test_insert_sample_data():
    """Test inserting sample data into tables"""
    print("\n4️⃣ Testing sample data insertion...")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Insert sample faculty
        cursor.execute('''
            INSERT INTO faculty (faculty_name, short_name, specialization)
            VALUES (?, ?, ?)
        ''', ('Dr. John Smith', 'JS', 'Computer Science'))
        
        # Insert sample subject
        cursor.execute('''
            INSERT INTO subject (subject_name, code, semester, lecture_credits, lab_credits)
            VALUES (?, ?, ?, ?, ?)
        ''', ('Data Structures', 'CS201', 2, 3, 2))
        
        conn.commit()
        print("✅ Sample data inserted successfully!")
        
        # Verify
        cursor.execute("SELECT * FROM faculty")
        faculty = cursor.fetchall()
        print(f"   Faculty count: {len(faculty)}")
        
        cursor.execute("SELECT * FROM subject")
        subjects = cursor.fetchall()
        print(f"   Subject count: {len(subjects)}")
        
    except Exception as e:
        print(f"❌ Error inserting data: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    test_database_creation()
    test_insert_sample_data()
    
    print("\n📝 Next Steps:")
    print("   1. Database is ready ✅")
    print("   2. Move to Module 2: File Upload System")
    print("   3. Run: python test_module2.py")