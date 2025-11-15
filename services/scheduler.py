# Scheduling logic
from database.db_setup import get_connection
import random

class TimetableScheduler:
    def __init__(self, config_id, semester):
        """
        Initialize scheduler
        
        Args:
            config_id: Academic configuration ID
            semester: Semester number to schedule
        """
        self.config_id = config_id
        self.semester = semester
        self.subjects = []
        self.faculty = []
        self.available_slots = []
        self.schedule = {}  # {slot_id: {subject_id, faculty_id}}
        self.faculty_load = {}  # {faculty_id: hours_assigned}
        
    def load_data(self):
        """Load subjects, faculty, and available slots from database"""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Load subjects for the semester
        cursor.execute('''
            SELECT * FROM subject WHERE semester = ?
        ''', (self.semester,))
        self.subjects = [dict(row) for row in cursor.fetchall()]
        
        # Load all faculty
        cursor.execute('SELECT * FROM faculty')
        self.faculty = [dict(row) for row in cursor.fetchall()]
        
        # Initialize faculty load tracking
        for faculty in self.faculty:
            self.faculty_load[faculty['id']] = 0
        
        # Load available (non-break) slots
        cursor.execute('''
            SELECT * FROM timetable_slots 
            WHERE config_id = ? AND is_break = 0
            ORDER BY day, slot_number
        ''', (self.config_id,))
        self.available_slots = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return len(self.subjects) > 0 and len(self.faculty) > 0
    
    def get_eligible_faculty(self, subject_id):
        """
        Get faculty members who can teach this subject
        For now, returns all faculty (can be enhanced with subject-faculty mapping)
        """
        # TODO: Check faculty_subject mapping table
        # For basic implementation, return all faculty
        return [f['id'] for f in self.faculty]
    
    def is_faculty_available(self, faculty_id, slot_id):
        """
        Check if faculty is available for this slot
        
        Returns: (available, reason)
        """
        # Get slot details
        slot = next((s for s in self.available_slots if s['id'] == slot_id), None)
        if not slot:
            return False, "Slot not found"
        
        # Check if faculty has this day available
        faculty = next((f for f in self.faculty if f['id'] == faculty_id), None)
        if not faculty:
            return False, "Faculty not found"
        
        # Parse availability (e.g., "Mon-Tue-Wed-Thu-Fri")
        available_days = faculty['availability'].split('-')
        day_map = {
            'Mon': 'Monday', 'Tue': 'Tuesday', 'Wed': 'Wednesday',
            'Thu': 'Thursday', 'Fri': 'Friday', 'Sat': 'Saturday'
        }
        full_days = [day_map.get(d, d) for d in available_days]
        
        if slot['day'] not in full_days:
            return False, f"Faculty not available on {slot['day']}"
        
        # Check if faculty is already assigned to another slot at this time
        for scheduled_slot_id, assignment in self.schedule.items():
            if assignment['faculty_id'] == faculty_id:
                scheduled_slot = next((s for s in self.available_slots if s['id'] == scheduled_slot_id), None)
                if scheduled_slot and scheduled_slot['day'] == slot['day']:
                    if scheduled_slot['start_time'] == slot['start_time']:
                        return False, "Faculty already assigned at this time"
        
        # Check max hours per week
        if self.faculty_load[faculty_id] >= faculty['max_hours_per_week']:
            return False, "Faculty weekly hour limit reached"
        
        return True, "Available"
    
    def is_slot_available(self, slot_id):
        """Check if slot is not yet assigned"""
        return slot_id not in self.schedule
    
    def find_consecutive_slots(self, day, start_slot_number, count=2):
        """
        Find consecutive available slots for labs
        
        Args:
            day: Day of the week
            start_slot_number: Starting slot number
            count: Number of consecutive slots needed
            
        Returns: List of slot IDs or None
        """
        slots = []
        
        for i in range(count):
            target_slot = next((s for s in self.available_slots 
                              if s['day'] == day and s['slot_number'] == start_slot_number + i), None)
            
            if not target_slot or not self.is_slot_available(target_slot['id']):
                return None
            
            slots.append(target_slot['id'])
        
        return slots
    
    def assign_slot(self, slot_id, subject_id, faculty_id, slot_type='lecture'):
        """
        Assign a subject and faculty to a slot
        
        Args:
            slot_id: Slot ID
            subject_id: Subject ID
            faculty_id: Faculty ID
            slot_type: 'lecture' or 'lab'
        """
        self.schedule[slot_id] = {
            'subject_id': subject_id,
            'faculty_id': faculty_id,
            'slot_type': slot_type
        }
        
        # Update faculty load
        self.faculty_load[faculty_id] += 1
    
    def remove_assignment(self, slot_id):
        """Remove an assignment (for backtracking)"""
        if slot_id in self.schedule:
            assignment = self.schedule[slot_id]
            self.faculty_load[assignment['faculty_id']] -= 1
            del self.schedule[slot_id]
    
    def schedule_lectures(self, subject):
        """
        Schedule lecture hours for a subject
        
        Args:
            subject: Subject dictionary
            
        Returns: (success, scheduled_count)
        """
        lecture_hours = subject['lecture_credits']
        if lecture_hours == 0:
            return True, 0
        
        eligible_faculty = self.get_eligible_faculty(subject['id'])
        if not eligible_faculty:
            return False, 0
        
        scheduled = 0
        attempts = 0
        max_attempts = len(self.available_slots) * 2
        
        # Try to distribute lectures across different days
        days_used = set()
        
        while scheduled < lecture_hours and attempts < max_attempts:
            attempts += 1
            
            # Try to find a slot on a day we haven't used yet
            preferred_slots = [s for s in self.available_slots 
                             if s['day'] not in days_used and self.is_slot_available(s['id'])]
            
            if not preferred_slots:
                # If all days used, use any available slot
                preferred_slots = [s for s in self.available_slots 
                                 if self.is_slot_available(s['id'])]
            
            if not preferred_slots:
                break
            
            # Randomly select a slot
            slot = random.choice(preferred_slots)
            
            # Try to assign a faculty
            for faculty_id in eligible_faculty:
                is_available, reason = self.is_faculty_available(faculty_id, slot['id'])
                
                if is_available:
                    self.assign_slot(slot['id'], subject['id'], faculty_id, 'lecture')
                    days_used.add(slot['day'])
                    scheduled += 1
                    break
        
        return scheduled == lecture_hours, scheduled
    
    def schedule_labs(self, subject):
        """
        Schedule lab hours for a subject (requires 2 consecutive slots)
        
        Args:
            subject: Subject dictionary
            
        Returns: (success, scheduled_blocks)
        """
        lab_hours = subject['lab_credits']
        if lab_hours == 0:
            return True, 0
        
        # Each lab session = 2 hours = 2 consecutive slots
        blocks_needed = lab_hours // 2
        if lab_hours % 2 != 0:
            blocks_needed += 1
        
        eligible_faculty = self.get_eligible_faculty(subject['id'])
        if not eligible_faculty:
            return False, 0
        
        scheduled_blocks = 0
        
        # Try each day
        days = list(set([s['day'] for s in self.available_slots]))
        
        for day in days:
            if scheduled_blocks >= blocks_needed:
                break
            
            # Get slots for this day
            day_slots = [s for s in self.available_slots if s['day'] == day]
            day_slots.sort(key=lambda x: x['slot_number'])
            
            # Try to find consecutive slots
            for i, slot in enumerate(day_slots):
                if scheduled_blocks >= blocks_needed:
                    break
                
                consecutive_slots = self.find_consecutive_slots(day, slot['slot_number'], 2)
                
                if consecutive_slots:
                    # Try to assign a faculty
                    for faculty_id in eligible_faculty:
                        # Check if faculty is available for both slots
                        all_available = all(
                            self.is_faculty_available(faculty_id, sid)[0] 
                            for sid in consecutive_slots
                        )
                        
                        if all_available:
                            # Assign both slots
                            for sid in consecutive_slots:
                                self.assign_slot(sid, subject['id'], faculty_id, 'lab')
                            
                            scheduled_blocks += 1
                            break
        
        return scheduled_blocks >= blocks_needed, scheduled_blocks
    
    def schedule_subject(self, subject):
        """
        Schedule both lectures and labs for a subject
        
        Returns: (success, stats)
        """
        stats = {
            'subject_name': subject['subject_name'],
            'code': subject['code'],
            'lectures_needed': subject['lecture_credits'],
            'lectures_scheduled': 0,
            'labs_needed': subject['lab_credits'],
            'labs_scheduled': 0,
            'success': False
        }
        
        # Schedule lectures
        lecture_success, lecture_count = self.schedule_lectures(subject)
        stats['lectures_scheduled'] = lecture_count
        
        # Schedule labs
        lab_success, lab_count = self.schedule_labs(subject)
        stats['labs_scheduled'] = lab_count * 2  # Each block = 2 hours
        
        stats['success'] = lecture_success and lab_success
        
        return stats['success'], stats
    
    def generate_schedule(self):
        """
        Main scheduling algorithm
        Uses greedy approach with priority ordering
        
        Returns: (success, statistics)
        """
        if not self.load_data():
            return False, {"error": "No data found for scheduling"}
        
        # Sort subjects by priority:
        # 1. Total hours (lecture + lab) - descending
        # 2. Lab hours - descending (labs need consecutive slots)
        self.subjects.sort(
            key=lambda x: (x['lecture_credits'] + x['lab_credits'], x['lab_credits']),
            reverse=True
        )
        
        results = {
            'total_subjects': len(self.subjects),
            'successfully_scheduled': 0,
            'partially_scheduled': 0,
            'failed': 0,
            'details': []
        }
        
        for subject in self.subjects:
            success, stats = self.schedule_subject(subject)
            
            if success:
                results['successfully_scheduled'] += 1
            elif stats['lectures_scheduled'] > 0 or stats['labs_scheduled'] > 0:
                results['partially_scheduled'] += 1
            else:
                results['failed'] += 1
            
            results['details'].append(stats)
        
        return True, results
    
    def save_schedule(self):
        """Save the generated schedule to database"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            for slot_id, assignment in self.schedule.items():
                cursor.execute('''
                    UPDATE timetable_slots 
                    SET subject_id = ?, faculty_id = ?, slot_type = ?
                    WHERE id = ?
                ''', (
                    assignment['subject_id'],
                    assignment['faculty_id'],
                    assignment['slot_type'],
                    slot_id
                ))
            
            conn.commit()
            return True, "Schedule saved successfully"
        
        except Exception as e:
            conn.rollback()
            return False, f"Error saving schedule: {str(e)}"
        
        finally:
            conn.close()
    
    def get_conflicts(self):
        """
        Check for any conflicts in the schedule
        
        Returns: List of conflicts
        """
        conflicts = []
        
        # Check faculty double-booking
        faculty_schedule = {}
        
        for slot_id, assignment in self.schedule.items():
            slot = next((s for s in self.available_slots if s['id'] == slot_id), None)
            if not slot:
                continue
            
            faculty_id = assignment['faculty_id']
            time_key = f"{slot['day']}_{slot['start_time']}"
            
            if faculty_id not in faculty_schedule:
                faculty_schedule[faculty_id] = {}
            
            if time_key in faculty_schedule[faculty_id]:
                conflicts.append({
                    'type': 'faculty_double_booking',
                    'faculty_id': faculty_id,
                    'day': slot['day'],
                    'time': slot['start_time'],
                    'slots': [faculty_schedule[faculty_id][time_key], slot_id]
                })
            else:
                faculty_schedule[faculty_id][time_key] = slot_id
        
        return conflicts