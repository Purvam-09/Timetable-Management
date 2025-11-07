"""
Timetable Service
Generates formatted timetable views for classes and faculty
"""

from database.db_setup import get_connection

def get_class_timetable_grid(config_id):
    """
    Generate class timetable in grid format
    Rows = Time slots, Columns = Days
    
    Returns: Dictionary with time_slots and grid data
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get configuration to know working days
    cursor.execute('SELECT * FROM academic_config WHERE id = ?', (config_id,))
    config_row = cursor.fetchone()
    
    if not config_row:
        conn.close()
        return None
    
    config = dict(config_row)
    
    # Determine days based on working_days
    if config['working_days'] == 'Mon-Fri':
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    else:
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    # Get all unique time slots (slot_number, start_time, end_time)
    cursor.execute('''
        SELECT DISTINCT slot_number, start_time, end_time, is_break
        FROM timetable_slots
        WHERE config_id = ?
        ORDER BY slot_number
    ''', (config_id,))
    
    time_slots = [dict(row) for row in cursor.fetchall()]
    
    # Get all slot assignments
    cursor.execute('''
        SELECT 
            ts.day,
            ts.slot_number,
            ts.start_time,
            ts.end_time,
            ts.is_break,
            ts.slot_type,
            s.subject_name,
            s.code as subject_code,
            f.short_name as faculty_short_name,
            f.faculty_name
        FROM timetable_slots ts
        LEFT JOIN subject s ON ts.subject_id = s.id
        LEFT JOIN faculty f ON ts.faculty_id = f.id
        WHERE ts.config_id = ?
        ORDER BY ts.day, ts.slot_number
    ''', (config_id,))
    
    all_slots = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Build grid: for each time slot, get data for each day
    grid = []
    
    for time_slot in time_slots:
        slot_number = time_slot['slot_number']
        row = {
            'slot_number': slot_number,
            'start_time': time_slot['start_time'],
            'end_time': time_slot['end_time'],
            'is_break': time_slot['is_break'],
            'days': {}
        }
        
        # For each day, find the slot data
        for day in days:
            slot_data = next(
                (s for s in all_slots 
                 if s['day'] == day and s['slot_number'] == slot_number),
                None
            )
            
            if slot_data:
                row['days'][day] = {
                    'is_break': slot_data['is_break'],
                    'subject_code': slot_data['subject_code'],
                    'subject_name': slot_data['subject_name'],
                    'faculty_short_name': slot_data['faculty_short_name'],
                    'faculty_name': slot_data['faculty_name'],
                    'slot_type': slot_data['slot_type']
                }
            else:
                row['days'][day] = {
                    'is_break': False,
                    'subject_code': None,
                    'subject_name': None,
                    'faculty_short_name': None,
                    'faculty_name': None,
                    'slot_type': None
                }
        
        grid.append(row)
    
    return {
        'config': config,
        'days': days,
        'time_slots': grid
    }

def get_class_timetable_multishift(config_id):
    """
    Generate class timetable for multi-shift configuration
    Returns separate grids for each shift
    
    Returns: Dictionary with shifts data
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get configuration
    cursor.execute('SELECT * FROM academic_config WHERE id = ?', (config_id,))
    config_row = cursor.fetchone()
    
    if not config_row:
        conn.close()
        return None
    
    config = dict(config_row)
    
    # Check if it's multi-shift
    if config['shift_mode'] != 'multi':
        conn.close()
        return get_class_timetable_grid(config_id)
    
    # Determine days
    if config['working_days'] == 'Mon-Fri':
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    else:
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    # Parse shift timings
    import json
    shift_timings = json.loads(config['shift_timings'])
    
    # Get all slot assignments
    cursor.execute('''
        SELECT 
            ts.day,
            ts.slot_number,
            ts.start_time,
            ts.end_time,
            ts.is_break,
            ts.slot_type,
            s.subject_name,
            s.code as subject_code,
            f.short_name as faculty_short_name,
            f.faculty_name
        FROM timetable_slots ts
        LEFT JOIN subject s ON ts.subject_id = s.id
        LEFT JOIN faculty f ON ts.faculty_id = f.id
        WHERE ts.config_id = ?
        ORDER BY ts.start_time, ts.slot_number
    ''', (config_id,))
    
    all_slots = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Organize slots by shift
    shifts_data = []
    
    for shift_info in shift_timings:
        shift_start = shift_info['start']
        shift_end = shift_info['end']
        shift_name = shift_info['name']
        
        # Filter slots for this shift
        shift_slots = [s for s in all_slots 
                      if s['start_time'] >= shift_start and s['start_time'] < shift_end]
        
        # Get unique time slots for this shift
        unique_times = {}
        for slot in shift_slots:
            key = (slot['slot_number'], slot['start_time'], slot['end_time'], slot['is_break'])
            if key not in unique_times:
                unique_times[key] = {
                    'slot_number': slot['slot_number'],
                    'start_time': slot['start_time'],
                    'end_time': slot['end_time'],
                    'is_break': slot['is_break']
                }
        
        time_slots = sorted(unique_times.values(), key=lambda x: x['start_time'])
        
        # Build grid for this shift
        grid = []
        for time_slot in time_slots:
            row = {
                'slot_number': time_slot['slot_number'],
                'start_time': time_slot['start_time'],
                'end_time': time_slot['end_time'],
                'is_break': time_slot['is_break'],
                'days': {}
            }
            
            for day in days:
                slot_data = next(
                    (s for s in shift_slots 
                     if s['day'] == day 
                     and s['slot_number'] == time_slot['slot_number']
                     and s['start_time'] == time_slot['start_time']),
                    None
                )
                
                if slot_data:
                    row['days'][day] = {
                        'is_break': slot_data['is_break'],
                        'subject_code': slot_data['subject_code'],
                        'subject_name': slot_data['subject_name'],
                        'faculty_short_name': slot_data['faculty_short_name'],
                        'faculty_name': slot_data['faculty_name'],
                        'slot_type': slot_data['slot_type']
                    }
                else:
                    row['days'][day] = {
                        'is_break': False,
                        'subject_code': None,
                        'subject_name': None,
                        'faculty_short_name': None,
                        'faculty_name': None,
                        'slot_type': None
                    }
            
            grid.append(row)
        
        shifts_data.append({
            'name': shift_name,
            'start_time': shift_start,
            'end_time': shift_end,
            'time_slots': grid
        })
    
    return {
        'config': config,
        'days': days,
        'is_multi_shift': True,
        'shifts': shifts_data
    }

def get_class_timetable(config_id):
    """
    Generate class timetable (all subjects for the semester)
    OLD FORMAT - Keep for compatibility
    
    Returns: Dictionary organized by day and time
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all slots with assignments
    cursor.execute('''
        SELECT 
            ts.id,
            ts.day,
            ts.slot_number,
            ts.start_time,
            ts.end_time,
            ts.is_break,
            ts.slot_type,
            s.subject_name,
            s.code as subject_code,
            f.short_name as faculty_short_name
        FROM timetable_slots ts
        LEFT JOIN subject s ON ts.subject_id = s.id
        LEFT JOIN faculty f ON ts.faculty_id = f.id
        WHERE ts.config_id = ?
        ORDER BY ts.day, ts.slot_number
    ''', (config_id,))
    
    slots = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Organize by day
    timetable = {}
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    for day in days_order:
        day_slots = [s for s in slots if s['day'] == day]
        if day_slots:
            timetable[day] = day_slots
    
    return timetable


def get_faculty_timetable(config_id, faculty_id=None):
    """
    Generate faculty timetable
    
    Args:
        config_id: Configuration ID
        faculty_id: Optional specific faculty ID, or None for all faculty
        
    Returns: Dictionary organized by faculty, then day
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if faculty_id:
        query = '''
            SELECT 
                ts.id,
                ts.day,
                ts.slot_number,
                ts.start_time,
                ts.end_time,
                ts.slot_type,
                s.subject_name,
                s.code as subject_code,
                f.id as faculty_id,
                f.faculty_name,
                f.short_name as faculty_short_name
            FROM timetable_slots ts
            JOIN subject s ON ts.subject_id = s.id
            JOIN faculty f ON ts.faculty_id = f.id
            WHERE ts.config_id = ? AND f.id = ?
            ORDER BY ts.day, ts.slot_number
        '''
        cursor.execute(query, (config_id, faculty_id))
    else:
        query = '''
            SELECT 
                ts.id,
                ts.day,
                ts.slot_number,
                ts.start_time,
                ts.end_time,
                ts.slot_type,
                s.subject_name,
                s.code as subject_code,
                f.id as faculty_id,
                f.faculty_name,
                f.short_name as faculty_short_name
            FROM timetable_slots ts
            JOIN subject s ON ts.subject_id = s.id
            JOIN faculty f ON ts.faculty_id = f.id
            WHERE ts.config_id = ?
            ORDER BY f.faculty_name, ts.day, ts.slot_number
        '''
        cursor.execute(query, (config_id,))
    
    slots = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Organize by faculty, then by day
    timetable = {}
    
    # Define days order
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    for slot in slots:
        fid = slot['faculty_id']
        
        if fid not in timetable:
            timetable[fid] = {
                'faculty_name': slot['faculty_name'],
                'short_name': slot['faculty_short_name'],
                'schedule': {}
            }
        
        day = slot['day']
        if day not in timetable[fid]['schedule']:
            timetable[fid]['schedule'][day] = []
        
        timetable[fid]['schedule'][day].append({
            'id': slot['id'],
            'slot_number': slot['slot_number'],
            'start_time': slot['start_time'],
            'end_time': slot['end_time'],
            'slot_type': slot['slot_type'],
            'subject_name': slot['subject_name'],
            'subject_code': slot['subject_code']
        })
    
    # Sort schedule by days
    for fid in timetable:
        sorted_schedule = {}
        for day in days_order:
            if day in timetable[fid]['schedule']:
                sorted_schedule[day] = timetable[fid]['schedule'][day]
        timetable[fid]['schedule'] = sorted_schedule
    
    return timetable

def get_faculty_timetable_grid(config_id, faculty_id):
    """
    Generate faculty timetable in grid format (similar to class timetable)
    Rows = Time slots, Columns = Days
    
    Args:
        config_id: Configuration ID
        faculty_id: Specific faculty ID
        
    Returns: Dictionary with time_slots and grid data
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get configuration
    cursor.execute('SELECT * FROM academic_config WHERE id = ?', (config_id,))
    config_row = cursor.fetchone()
    
    if not config_row:
        conn.close()
        return None
    
    config = dict(config_row)
    
    # Get faculty details
    cursor.execute('SELECT * FROM faculty WHERE id = ?', (faculty_id,))
    faculty_row = cursor.fetchone()
    
    if not faculty_row:
        conn.close()
        return None
    
    faculty = dict(faculty_row)
    
    # Determine days based on working_days
    if config['working_days'] == 'Mon-Fri':
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    else:
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    # Get all unique time slots
    cursor.execute('''
        SELECT DISTINCT slot_number, start_time, end_time, is_break
        FROM timetable_slots
        WHERE config_id = ?
        ORDER BY slot_number
    ''', (config_id,))
    
    time_slots = [dict(row) for row in cursor.fetchall()]
    
    # Get all assignments for this faculty
    cursor.execute('''
        SELECT 
            ts.day,
            ts.slot_number,
            ts.start_time,
            ts.end_time,
            ts.is_break,
            ts.slot_type,
            s.subject_name,
            s.code as subject_code
        FROM timetable_slots ts
        LEFT JOIN subject s ON ts.subject_id = s.id
        WHERE ts.config_id = ? AND ts.faculty_id = ?
        ORDER BY ts.day, ts.slot_number
    ''', (config_id, faculty_id))
    
    faculty_slots = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Build grid: for each time slot, get data for each day
    grid = []
    
    for time_slot in time_slots:
        slot_number = time_slot['slot_number']
        row = {
            'slot_number': slot_number,
            'start_time': time_slot['start_time'],
            'end_time': time_slot['end_time'],
            'is_break': time_slot['is_break'],
            'days': {}
        }
        
        # For each day, find the slot data
        for day in days:
            slot_data = next(
                (s for s in faculty_slots 
                 if s['day'] == day and s['slot_number'] == slot_number),
                None
            )
            
            if slot_data:
                row['days'][day] = {
                    'is_break': slot_data['is_break'],
                    'subject_code': slot_data['subject_code'],
                    'subject_name': slot_data['subject_name'],
                    'slot_type': slot_data['slot_type']
                }
            else:
                # Check if this time slot exists for this day (might be break or free)
                general_slot = next(
                    (s for s in time_slots 
                     if s['slot_number'] == slot_number),
                    None
                )
                
                if general_slot and general_slot['is_break']:
                    row['days'][day] = {
                        'is_break': True,
                        'subject_code': None,
                        'subject_name': None,
                        'slot_type': None
                    }
                else:
                    row['days'][day] = {
                        'is_break': False,
                        'subject_code': None,
                        'subject_name': None,
                        'slot_type': None
                    }
        
        grid.append(row)
    
    # Calculate total hours
    total_hours = len([s for s in faculty_slots if not s['is_break']])
    
    return {
        'config': config,
        'faculty': faculty,
        'days': days,
        'time_slots': grid,
        'total_hours': total_hours
    }


def get_all_faculty_list():
    """Get list of all faculty for dropdown"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, faculty_name, short_name 
        FROM faculty 
        ORDER BY faculty_name
    ''')
    
    faculty_list = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return faculty_list


def get_faculty_timetable_multishift(config_id, faculty_id):
    """
    Generate faculty timetable for multi-shift configuration
    Returns separate grids for each shift
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get configuration
    cursor.execute('SELECT * FROM academic_config WHERE id = ?', (config_id,))
    config_row = cursor.fetchone()
    
    if not config_row:
        conn.close()
        return None
    
    config = dict(config_row)
    
    # Check if it's multi-shift
    if config['shift_mode'] != 'multi':
        conn.close()
        return get_faculty_timetable_grid(config_id, faculty_id)
    
    # Get faculty details
    cursor.execute('SELECT * FROM faculty WHERE id = ?', (faculty_id,))
    faculty_row = cursor.fetchone()
    
    if not faculty_row:
        conn.close()
        return None
    
    faculty = dict(faculty_row)
    
    # Determine days
    if config['working_days'] == 'Mon-Fri':
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    else:
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    # Parse shift timings
    import json
    shift_timings = json.loads(config['shift_timings'])
    
    # Get all assignments for this faculty
    cursor.execute('''
        SELECT 
            ts.day, ts.slot_number, ts.start_time, ts.end_time,
            ts.is_break, ts.slot_type,
            s.subject_name, s.code as subject_code
        FROM timetable_slots ts
        LEFT JOIN subject s ON ts.subject_id = s.id
        WHERE ts.config_id = ? AND ts.faculty_id = ?
        ORDER BY ts.start_time, ts.slot_number
    ''', (config_id, faculty_id))
    
    faculty_slots = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Organize slots by shift
    shifts_data = []
    total_hours = 0
    
    for shift_info in shift_timings:
        shift_start = shift_info['start']
        shift_end = shift_info['end']
        shift_name = shift_info['name']
        
        # Filter slots for this shift
        shift_slots = [s for s in faculty_slots 
                      if s['start_time'] >= shift_start and s['start_time'] < shift_end]
        
        # Get unique time slots for this shift
        unique_times = {}
        for slot in shift_slots:
            key = (slot['slot_number'], slot['start_time'], slot['end_time'], slot['is_break'])
            if key not in unique_times:
                unique_times[key] = {
                    'slot_number': slot['slot_number'],
                    'start_time': slot['start_time'],
                    'end_time': slot['end_time'],
                    'is_break': slot['is_break']
                }
        
        time_slots = sorted(unique_times.values(), key=lambda x: x['start_time'])
        
        # Build grid for this shift
        grid = []
        for time_slot in time_slots:
            row = {
                'slot_number': time_slot['slot_number'],
                'start_time': time_slot['start_time'],
                'end_time': time_slot['end_time'],
                'is_break': time_slot['is_break'],
                'days': {}
            }
            
            for day in days:
                slot_data = next(
                    (s for s in shift_slots 
                     if s['day'] == day 
                     and s['slot_number'] == time_slot['slot_number']
                     and s['start_time'] == time_slot['start_time']),
                    None
                )
                
                if slot_data:
                    row['days'][day] = {
                        'is_break': slot_data['is_break'],
                        'subject_code': slot_data['subject_code'],
                        'subject_name': slot_data['subject_name'],
                        'slot_type': slot_data['slot_type']
                    }
                    if not slot_data['is_break']:
                        total_hours += 1
                else:
                    if time_slot['is_break']:
                        row['days'][day] = {
                            'is_break': True,
                            'subject_code': None,
                            'subject_name': None,
                            'slot_type': None
                        }
                    else:
                        row['days'][day] = {
                            'is_break': False,
                            'subject_code': None,
                            'subject_name': None,
                            'slot_type': None
                        }
            
            grid.append(row)
        
        shifts_data.append({
            'name': shift_name,
            'start_time': shift_start,
            'end_time': shift_end,
            'time_slots': grid
        })
    
    return {
        'config': config,
        'faculty': faculty,
        'days': days,
        'is_multi_shift': True,
        'shifts': shifts_data,
        'total_hours': total_hours
    }

def get_timetable_statistics(config_id):
    """
    Get statistics about the generated timetable
    
    Returns: Dictionary with various statistics
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    # Total slots
    cursor.execute('SELECT COUNT(*) FROM timetable_slots WHERE config_id = ?', (config_id,))
    stats['total_slots'] = cursor.fetchone()[0]
    
    # Assigned slots
    cursor.execute('''
        SELECT COUNT(*) FROM timetable_slots 
        WHERE config_id = ? AND subject_id IS NOT NULL
    ''', (config_id,))
    stats['assigned_slots'] = cursor.fetchone()[0]
    
    # Break slots
    cursor.execute('''
        SELECT COUNT(*) FROM timetable_slots 
        WHERE config_id = ? AND is_break = 1
    ''', (config_id,))
    stats['break_slots'] = cursor.fetchone()[0]
    
    # Available slots
    stats['available_slots'] = stats['total_slots'] - stats['break_slots']
    stats['unassigned_slots'] = stats['available_slots'] - stats['assigned_slots']
    stats['utilization_percent'] = (stats['assigned_slots'] / stats['available_slots'] * 100) if stats['available_slots'] > 0 else 0
    
    # Faculty workload
    cursor.execute('''
        SELECT f.faculty_name, f.short_name, COUNT(ts.id) as hours
        FROM faculty f
        LEFT JOIN timetable_slots ts ON f.id = ts.faculty_id AND ts.config_id = ?
        GROUP BY f.id
        ORDER BY hours DESC
    ''', (config_id,))
    
    stats['faculty_workload'] = [dict(row) for row in cursor.fetchall()]
    
    # Subject distribution
    cursor.execute('''
        SELECT s.subject_name, s.code, 
               SUM(CASE WHEN ts.slot_type = 'lecture' THEN 1 ELSE 0 END) as lectures,
               SUM(CASE WHEN ts.slot_type = 'lab' THEN 1 ELSE 0 END) as labs
        FROM subject s
        LEFT JOIN timetable_slots ts ON s.id = ts.subject_id AND ts.config_id = ?
        GROUP BY s.id
        HAVING lectures > 0 OR labs > 0
        ORDER BY s.subject_name
    ''', (config_id,))
    
    stats['subject_distribution'] = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return stats


def format_timetable_cell(slot):
    """
    Format a timetable cell for display
    
    Returns: String representation
    """
    if slot['is_break']:
        return "BREAK"
    
    if not slot.get('subject_code'):
        return "-"
    
    slot_type_marker = "🔬" if slot.get('slot_type') == 'lab' else "📚"
    return f"{slot_type_marker} {slot['subject_code']}-{slot['faculty_short_name']}"


def print_class_timetable(config_id):
    """Print formatted class timetable to console"""
    timetable = get_class_timetable(config_id)
    
    print("\n" + "=" * 100)
    print("  CLASS TIMETABLE")
    print("=" * 100)
    
    for day, slots in timetable.items():
        print(f"\n📅 {day}")
        print("-" * 100)
        
        for slot in slots:
            time_range = f"{slot['start_time']} - {slot['end_time']}"
            content = format_timetable_cell(slot)
            print(f"   {time_range:15} | {content}")


def print_faculty_timetable(config_id, faculty_id=None):
    """Print formatted faculty timetable to console"""
    timetable = get_faculty_timetable(config_id, faculty_id)
    
    print("\n" + "=" * 100)
    print("  FACULTY TIMETABLE")
    print("=" * 100)
    
    for fid, data in timetable.items():
        print(f"\n👤 {data['faculty_name']} ({data['short_name']})")
        print("-" * 100)
        
        for day, slots in data['schedule'].items():
            print(f"\n  📅 {day}")
            for slot in slots:
                time_range = f"{slot['start_time']} - {slot['end_time']}"
                slot_type = "🔬 LAB" if slot['slot_type'] == 'lab' else "📚 LECTURE"
                print(f"     {time_range:15} | {slot_type:12} | {slot['subject_code']} - {slot['subject_name']}")