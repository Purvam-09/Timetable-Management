"""
Data Service
Handles database insertion and retrieval operations
"""

from database.db_setup import get_connection
import sqlite3

def insert_faculty_data(df):
    """
    Insert faculty data into database
    Handles duplicates by updating existing records
    
    Args:
        df: pandas DataFrame with faculty data
        
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
                # Check if faculty with this short_name already exists
                cursor.execute('SELECT id FROM faculty WHERE short_name = ?', 
                             (row['short_name'],))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record
                    cursor.execute('''
                        UPDATE faculty 
                        SET faculty_name = ?, 
                            specialization = ?,
                            availability = ?,
                            max_hours_per_week = ?
                        WHERE short_name = ?
                    ''', (
                        row['faculty_name'],
                        row.get('specialization', 'General'),
                        row.get('availability', 'Mon,Tue,Wed,Thu,Fri,Sat'),
                        row.get('max_hours_per_week', 24),
                        row['short_name']
                    ))
                    updated += 1
                else:
                    # Insert new record
                    cursor.execute('''
                        INSERT INTO faculty (faculty_name, short_name, specialization, 
                                           availability, max_hours_per_week)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        row['faculty_name'],
                        row['short_name'],
                        row.get('specialization', 'General'),
                        row.get('availability', 'Mon,Tue,Wed,Thu,Fri,Sat'),
                        row.get('max_hours_per_week', 24)
                    ))
                    inserted += 1
                
            except Exception as e:
                errors.append(f"Row {_ + 2}: {str(e)}")
        
        conn.commit()
        
        # Log upload history
        cursor.execute('''
            INSERT INTO upload_history (file_type, filename, records_count, status)
            VALUES (?, ?, ?, ?)
        ''', ('faculty', 'faculty_data', inserted + updated, 'success'))
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

def insert_subject_data(df):
    """
    Insert subject data into database
    Handles duplicates by updating existing records
    
    Args:
        df: pandas DataFrame with subject data
        
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
                # Check if subject with this code already exists
                cursor.execute('SELECT id FROM subject WHERE code = ?', 
                             (row['code'],))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record
                    cursor.execute('''
                        UPDATE subject 
                        SET subject_name = ?,
                            semester = ?,
                            lecture_credits = ?,
                            lab_credits = ?
                        WHERE code = ?
                    ''', (
                        row['subject_name'],
                        int(row['semester']),
                        int(row['lecture_credits']),
                        int(row['lab_credits']),
                        row['code']
                    ))
                    updated += 1
                else:
                    # Insert new record
                    cursor.execute('''
                        INSERT INTO subject (subject_name, code, semester, 
                                           lecture_credits, lab_credits)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        row['subject_name'],
                        row['code'],
                        int(row['semester']),
                        int(row['lecture_credits']),
                        int(row['lab_credits'])
                    ))
                    inserted += 1
                
            except Exception as e:
                errors.append(f"Row {_ + 2}: {str(e)}")
        
        conn.commit()
        
        # Log upload history
        cursor.execute('''
            INSERT INTO upload_history (file_type, filename, records_count, status)
            VALUES (?, ?, ?, ?)
        ''', ('subject', 'subject_data', inserted + updated, 'success'))
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

def get_all_faculty():
    """Get all faculty from database"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM faculty ORDER BY faculty_name')
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_all_subjects():
    """Get all subjects from database"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM subject ORDER BY semester, subject_name')
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_subjects_by_semester(semester):
    """Get subjects for a specific semester"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM subject WHERE semester = ? ORDER BY subject_name', 
                  (semester,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def clear_all_data():
    """Clear all data from tables (for testing)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM timetable_slots')
        cursor.execute('DELETE FROM faculty_subject')
        cursor.execute('DELETE FROM subject')
        cursor.execute('DELETE FROM faculty')
        cursor.execute('DELETE FROM academic_config')
        cursor.execute('DELETE FROM upload_history')
        
        conn.commit()
        return True, "All data cleared successfully"
    
    except Exception as e:
        conn.rollback()
        return False, f"Error clearing data: {str(e)}"
    
    finally:
        conn.close()

def get_database_stats():
    """Get statistics about current database state"""
    conn = get_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    cursor.execute('SELECT COUNT(*) FROM faculty')
    stats['faculty_count'] = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM subject')
    stats['subject_count'] = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM faculty_subject')
    stats['mappings_count'] = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT semester) FROM subject')
    stats['semesters_count'] = cursor.fetchone()[0]
    
    conn.close()
    
    return stats