"""
Location/Classroom Management Service
Handles location data insertion and retrieval
"""

from database.db_setup import get_connection
import sqlite3

def insert_location_data(df):
    """
    Insert location/classroom data into database
    Handles duplicates by updating existing records
    
    Args:
        df: pandas DataFrame with location data
        
    Returns:
        (success, message, stats)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    inserted = 0
    updated = 0
    errors = []
    
    try:
        for _, row in df.iterrows():
            try:
                # Check if location with this room_number already exists
                cursor.execute('SELECT id FROM locations WHERE room_number = ?', 
                             (row['room_number'],))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record
                    cursor.execute('''
                        UPDATE locations 
                        SET building = ?,
                            floor = ?,
                            room_type = ?,
                            capacity = ?
                        WHERE room_number = ?
                    ''', (
                        row.get('building', 'Main'),
                        int(row.get('floor', 0)),
                        row.get('room_type', 'Classroom'),
                        int(row.get('capacity', 60)),
                        row['room_number']
                    ))
                    updated += 1
                else:
                    # Insert new record
                    cursor.execute('''
                        INSERT INTO locations (room_number, building, floor, room_type, capacity)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        row['room_number'],
                        row.get('building', 'Main'),
                        int(row.get('floor', 0)),
                        row.get('room_type', 'Classroom'),
                        int(row.get('capacity', 60))
                    ))
                    inserted += 1
                
            except Exception as e:
                errors.append(f"Row {_ + 2}: {str(e)}")
        
        conn.commit()
        
        # Log upload history
        cursor.execute('''
            INSERT INTO upload_history (file_type, filename, records_count, status)
            VALUES (?, ?, ?, ?)
        ''', ('location', 'location_data', inserted + updated, 'success'))
        conn.commit()
        
        stats = {
            'inserted': inserted,
            'updated': updated,
            'total': inserted + updated,
            'errors': len(errors)
        }
        
        message = f"Successfully processed {stats['total']} records "
        message += f"({inserted} new, {updated} updated)"
        
        if errors:
            message += f" with {len(errors)} errors"
        
        return True, message, stats
        
    except Exception as e:
        conn.rollback()
        return False, f"Database error: {str(e)}", None
    
    finally:
        conn.close()

def get_all_locations():
    """Get all locations from database"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM locations 
        ORDER BY building, floor, room_number
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_locations_by_type(room_type):
    """Get locations filtered by room type"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM locations 
        WHERE room_type = ?
        ORDER BY building, floor, room_number
    ''', (room_type,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_location_by_id(location_id):
    """Get a specific location by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM locations WHERE id = ?', (location_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None

def get_location_statistics():
    """Get statistics about locations"""
    conn = get_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    # Total locations
    cursor.execute('SELECT COUNT(*) FROM locations')
    stats['total_locations'] = cursor.fetchone()[0]
    
    # By room type
    cursor.execute('''
        SELECT room_type, COUNT(*) as count
        FROM locations
        GROUP BY room_type
        ORDER BY count DESC
    ''')
    stats['by_type'] = [dict(row) for row in cursor.fetchall()]
    
    # By building
    cursor.execute('''
        SELECT building, COUNT(*) as count
        FROM locations
        GROUP BY building
        ORDER BY building
    ''')
    stats['by_building'] = [dict(row) for row in cursor.fetchall()]
    
    # Total capacity
    cursor.execute('SELECT SUM(capacity) FROM locations')
    stats['total_capacity'] = cursor.fetchone()[0] or 0
    
    # Average capacity
    cursor.execute('SELECT AVG(capacity) FROM locations')
    stats['avg_capacity'] = round(cursor.fetchone()[0] or 0, 1)
    
    conn.close()
    
    return stats

def delete_location(location_id):
    """Delete a location"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM locations WHERE id = ?', (location_id,))
        conn.commit()
        return True, "Location deleted successfully"
    except Exception as e:
        conn.rollback()
        return False, f"Error deleting location: {str(e)}"
    finally:
        conn.close()

def search_locations(query):
    """Search locations by room number or building"""
    conn = get_connection()
    cursor = conn.cursor()
    
    search_pattern = f"%{query}%"
    cursor.execute('''
        SELECT * FROM locations
        WHERE room_number LIKE ? OR building LIKE ?
        ORDER BY room_number
    ''', (search_pattern, search_pattern))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]