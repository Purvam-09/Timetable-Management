"""
Session Service
Manages fresh sessions and data cleanup
"""

from database.db_setup import get_connection
from datetime import datetime
import json

def create_new_session():
    """
    Create a new session and clear all previous data
    Returns: (success, message, session_id)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Clear all existing data
        cursor.execute('DELETE FROM timetable_slots')
        cursor.execute('DELETE FROM faculty_subject')
        cursor.execute('DELETE FROM subject')
        cursor.execute('DELETE FROM faculty')
        cursor.execute('DELETE FROM academic_config')
        
        # Create session record
        cursor.execute('''
            INSERT INTO upload_history (file_type, filename, records_count, status)
            VALUES (?, ?, ?, ?)
        ''', ('session_start', 'NEW_SESSION', 0, 'active'))
        
        session_id = cursor.lastrowid
        
        conn.commit()
        
        return True, "New session created. All previous data cleared.", session_id
    
    except Exception as e:
        conn.rollback()
        return False, f"Error creating session: {str(e)}", None
    
    finally:
        conn.close()

def get_current_session():
    """
    Get information about current session
    Returns: Dictionary with session info or None
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get latest session start
    cursor.execute('''
        SELECT * FROM upload_history 
        WHERE file_type = 'session_start' 
        ORDER BY id DESC LIMIT 1
    ''')
    
    session = cursor.fetchone()
    
    if not session:
        conn.close()
        return None
    
    session_dict = dict(session)
    
    # Get counts since session start
    session_id = session_dict['id']
    
    # Faculty count
    cursor.execute('SELECT COUNT(*) FROM faculty')
    faculty_count = cursor.fetchone()[0]
    
    # Subject count
    cursor.execute('SELECT COUNT(*) FROM subject')
    subject_count = cursor.fetchone()[0]
    
    # Config status
    cursor.execute('SELECT * FROM academic_config WHERE is_active = 1')
    config = cursor.fetchone()
    has_config = config is not None
    
    # Timetable status
    cursor.execute('SELECT COUNT(*) FROM timetable_slots WHERE subject_id IS NOT NULL')
    has_timetable = cursor.fetchone()[0] > 0
    
    conn.close()
    
    return {
        'session_id': session_id,
        'started_at': session_dict['uploaded_at'],
        'faculty_count': faculty_count,
        'subject_count': subject_count,
        'has_config': has_config,
        'has_timetable': has_timetable,
        'is_ready': faculty_count > 0 and subject_count > 0
    }

def clear_timetable_only():
    """
    Clear only timetable data, keep faculty and subjects
    Useful when regenerating timetable
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM timetable_slots')
        cursor.execute('UPDATE academic_config SET is_active = 0')
        
        conn.commit()
        return True, "Timetable data cleared"
    
    except Exception as e:
        conn.rollback()
        return False, f"Error: {str(e)}"
    
    finally:
        conn.close()

def replace_faculty_data():
    """
    Prepare for new faculty upload by clearing old data
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Clear faculty and dependent data
        cursor.execute('DELETE FROM timetable_slots')
        cursor.execute('DELETE FROM faculty_subject')
        cursor.execute('DELETE FROM faculty')
        cursor.execute('UPDATE academic_config SET is_active = 0')
        
        conn.commit()
        return True, "Ready for new faculty data"
    
    except Exception as e:
        conn.rollback()
        return False, f"Error: {str(e)}"
    
    finally:
        conn.close()

def replace_subject_data():
    """
    Prepare for new subject upload by clearing old data
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Clear subjects and dependent data
        cursor.execute('DELETE FROM timetable_slots')
        cursor.execute('DELETE FROM faculty_subject')
        cursor.execute('DELETE FROM subject')
        cursor.execute('UPDATE academic_config SET is_active = 0')
        
        conn.commit()
        return True, "Ready for new subject data"
    
    except Exception as e:
        conn.rollback()
        return False, f"Error: {str(e)}"
    
    finally:
        conn.close()

def get_session_summary():
    """
    Get detailed summary of current session
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    summary = {}
    
    # Recent uploads
    cursor.execute('''
        SELECT file_type, filename, records_count, uploaded_at 
        FROM upload_history 
        WHERE file_type != 'session_start'
        ORDER BY id DESC 
        LIMIT 10
    ''')
    
    summary['recent_uploads'] = [dict(row) for row in cursor.fetchall()]
    
    # Faculty list
    cursor.execute('SELECT faculty_name, short_name FROM faculty ORDER BY faculty_name')
    summary['faculty_list'] = [dict(row) for row in cursor.fetchall()]
    
    # Subject list by semester
    cursor.execute('''
        SELECT semester, COUNT(*) as count 
        FROM subject 
        GROUP BY semester 
        ORDER BY semester
    ''')
    summary['subjects_by_semester'] = [dict(row) for row in cursor.fetchall()]
    
    # Active configuration
    cursor.execute('SELECT * FROM academic_config WHERE is_active = 1')
    config = cursor.fetchone()
    summary['active_config'] = dict(config) if config else None
    
    # Timetable status
    cursor.execute('''
        SELECT 
            COUNT(*) as total_slots,
            SUM(CASE WHEN subject_id IS NOT NULL THEN 1 ELSE 0 END) as assigned_slots,
            SUM(CASE WHEN is_break = 1 THEN 1 ELSE 0 END) as break_slots
        FROM timetable_slots
    ''')
    
    tt_stats = cursor.fetchone()
    summary['timetable_stats'] = dict(tt_stats) if tt_stats else None
    
    conn.close()
    
    return summary