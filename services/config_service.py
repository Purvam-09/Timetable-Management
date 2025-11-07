"""
Configuration Service
Handles academic configuration and timetable slot generation
"""

from database.db_setup import get_connection
from datetime import datetime, timedelta
import json

def validate_academic_year(year):
    """Validate academic year format (e.g., 2024-2025)"""
    try:
        parts = year.split('-')
        if len(parts) != 2:
            return False
        
        year1, year2 = int(parts[0]), int(parts[1])
        
        # Check if second year is exactly 1 more than first
        if year2 != year1 + 1:
            return False
        
        # Check if years are reasonable
        current_year = datetime.now().year
        if year1 < current_year - 5 or year1 > current_year + 5:
            return False
        
        return True
    except:
        return False

def validate_term_semester(term, semester):
    """
    Validate term and semester combination
    Jan-June: Sem 2,4,6,8 (Even)
    July-Dec: Sem 1,3,5,7 (Odd)
    """
    semester = int(semester)
    
    if semester < 1 or semester > 8:
        return False, "Semester must be between 1 and 8"
    
    if term == "Jan-June":
        if semester % 2 != 0:
            return False, "Jan-June term should have even semesters (2,4,6,8)"
    elif term == "July-Dec":
        if semester % 2 == 0:
            return False, "July-Dec term should have odd semesters (1,3,5,7)"
    else:
        return False, "Invalid term"
    
    return True, "Valid combination"

def parse_shift_timings(shift_mode, shift_data):
    """
    Parse shift timing data
    
    For single shift: {"start": "09:00", "end": "17:00"}
    For multi shift: [{"name": "Morning", "start": "08:00", "end": "13:00"}, ...]
    
    Returns: (success, parsed_data_or_error)
    """
    try:
        if shift_mode == "single":
            # Validate single shift
            if not all(k in shift_data for k in ['start', 'end']):
                return False, "Missing start or end time for single shift"
            
            # Validate time format
            datetime.strptime(shift_data['start'], '%H:%M')
            datetime.strptime(shift_data['end'], '%H:%M')
            
            return True, shift_data
        
        elif shift_mode == "multi":
            # Validate multi shift
            if not isinstance(shift_data, list) or len(shift_data) == 0:
                return False, "Multi-shift must have at least one shift"
            
            for shift in shift_data:
                if not all(k in shift for k in ['name', 'start', 'end']):
                    return False, f"Shift missing required fields"
                
                # Validate time format
                datetime.strptime(shift['start'], '%H:%M')
                datetime.strptime(shift['end'], '%H:%M')
            
            return True, shift_data
        
        else:
            return False, "Invalid shift mode"
    
    except Exception as e:
        return False, f"Error parsing shift timings: {str(e)}"

def save_academic_config(academic_year, term, semester, working_days, shift_mode, shift_timings):
    """
    Save academic configuration to database
    
    Returns: (success, message, config_id)
    """
    # Validate inputs
    if not validate_academic_year(academic_year):
        return False, "Invalid academic year format (use YYYY-YYYY)", None
    
    is_valid, message = validate_term_semester(term, semester)
    if not is_valid:
        return False, message, None
    
    if working_days not in ['Mon-Fri', 'Mon-Sat']:
        return False, "Working days must be 'Mon-Fri' or 'Mon-Sat'", None
    
    # Parse shift timings
    success, shift_data = parse_shift_timings(shift_mode, shift_timings)
    if not success:
        return False, shift_data, None
    
    # Save to database
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Deactivate previous configurations
        cursor.execute('UPDATE academic_config SET is_active = 0')
        
        # Insert new configuration
        cursor.execute('''
            INSERT INTO academic_config (academic_year, term, semester, working_days, 
                                        shift_mode, shift_timings, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', (
            academic_year,
            term,
            int(semester),
            working_days,
            shift_mode,
            json.dumps(shift_data)
        ))
        
        config_id = cursor.lastrowid
        conn.commit()
        
        return True, "Configuration saved successfully", config_id
    
    except Exception as e:
        conn.rollback()
        return False, f"Database error: {str(e)}", None
    
    finally:
        conn.close()

def get_active_config():
    """Get currently active academic configuration"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM academic_config WHERE is_active = 1 ORDER BY id DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    
    if row:
        config = dict(row)
        config['shift_timings'] = json.loads(config['shift_timings'])
        return config
    
    return None

def generate_time_slots(config_id):
    """
    Generate time slots for the given configuration
    Includes breaks and lunch
    
    Returns: (success, message, slots_count)
    """
    # Get configuration
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM academic_config WHERE id = ?', (config_id,))
    config = cursor.fetchone()
    
    if not config:
        conn.close()
        return False, "Configuration not found", 0
    
    config = dict(config)
    working_days = config['working_days']
    shift_mode = config['shift_mode']
    shift_timings = json.loads(config['shift_timings'])
    
    # Determine days
    if working_days == 'Mon-Fri':
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    else:
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    slots_created = 0
    
    try:
        # Clear existing slots for this config
        cursor.execute('DELETE FROM timetable_slots WHERE config_id = ?', (config_id,))
        
        if shift_mode == 'single':
            # Single shift slot generation
            start_time = datetime.strptime(shift_timings['start'], '%H:%M')
            end_time = datetime.strptime(shift_timings['end'], '%H:%M')
            
            for day in days:
                slot_number = 1
                current_time = start_time
                
                while current_time < end_time:
                    slot_end = current_time + timedelta(hours=1)
                    
                    # Check if this is break time (after 2 hours)
                    is_break = 0
                    if slot_number == 3:  # Short break after 2nd hour
                        is_break = 1
                        slot_end = current_time + timedelta(minutes=15)
                    elif slot_number == 5:  # Lunch break
                        is_break = 1
                        slot_end = current_time + timedelta(minutes=45)
                    
                    # Don't create slot if it exceeds end time
                    if slot_end > end_time:
                        break
                    
                    cursor.execute('''
                        INSERT INTO timetable_slots 
                        (config_id, day, slot_number, start_time, end_time, is_break)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        config_id,
                        day,
                        slot_number,
                        current_time.strftime('%H:%M'),
                        slot_end.strftime('%H:%M'),
                        is_break
                    ))
                    
                    slots_created += 1
                    slot_number += 1
                    current_time = slot_end
        
        elif shift_mode == 'multi':
            # Multi-shift slot generation
            for shift in shift_timings:
                start_time = datetime.strptime(shift['start'], '%H:%M')
                end_time = datetime.strptime(shift['end'], '%H:%M')
                
                for day in days:
                    slot_number = 1
                    current_time = start_time
                    
                    while current_time < end_time:
                        slot_end = current_time + timedelta(hours=1)
                        
                        # Add break logic for multi-shift
                        is_break = 0
                        if slot_number == 3:
                            is_break = 1
                            slot_end = current_time + timedelta(minutes=15)
                        
                        if slot_end > end_time:
                            break
                        
                        cursor.execute('''
                            INSERT INTO timetable_slots 
                            (config_id, day, slot_number, start_time, end_time, is_break)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            config_id,
                            day,
                            slot_number,
                            current_time.strftime('%H:%M'),
                            slot_end.strftime('%H:%M'),
                            is_break
                        ))
                        
                        slots_created += 1
                        slot_number += 1
                        current_time = slot_end
        
        conn.commit()
        return True, f"Generated {slots_created} time slots", slots_created
    
    except Exception as e:
        conn.rollback()
        return False, f"Error generating slots: {str(e)}", 0
    
    finally:
        conn.close()

def get_time_slots(config_id, day=None):
    """
    Get time slots for a configuration
    
    Args:
        config_id: Configuration ID
        day: Optional day filter
        
    Returns: List of slots
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if day:
        cursor.execute('''
            SELECT * FROM timetable_slots 
            WHERE config_id = ? AND day = ?
            ORDER BY slot_number
        ''', (config_id, day))
    else:
        cursor.execute('''
            SELECT * FROM timetable_slots 
            WHERE config_id = ?
            ORDER BY day, slot_number
        ''', (config_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_available_slots(config_id, day=None):
    """Get only non-break slots available for scheduling"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = '''
        SELECT * FROM timetable_slots 
        WHERE config_id = ? AND is_break = 0
    '''
    params = [config_id]
    
    if day:
        query += ' AND day = ?'
        params.append(day)
    
    query += ' ORDER BY day, slot_number'
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]