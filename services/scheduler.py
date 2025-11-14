# services/enhanced_scheduler.py
"""
Enhanced Timetable Scheduler with:
- Better conflict detection
- Room assignment
- Faculty preference optimization
- Load balancing
"""

from database.db_setup import get_connection
import random
from collections import defaultdict
from typing import List, Dict, Tuple, Optional

class TimetableScheduler:
    def __init__(self, config_id, semester):
        self.config_id = config_id
        self.semester = semester
        
        # Core data
        self.subjects = []
        self.faculty = []
        self.available_slots = []
        self.locations = []
        
        # Scheduling state
        self.schedule = {}  # {slot_id: assignment}
        self.faculty_load = {}  # {faculty_id: hours}
        self.room_assignments = {}  # {slot_id: room_id}
        self.day_slot_map = defaultdict(list)  # {day: [slot_ids]}
        
        # Constraints
        self.max_consecutive_hours = 3
        self.min_gap_between_sessions = 0  # slots
        
        # Statistics
        self.conflicts = []
        self.warnings = []
        
    def load_data(self) -> bool:
        """Load all necessary data from database"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Load subjects for semester
            cursor.execute('''
                SELECT * FROM subject WHERE semester = ?
            ''', (self.semester,))
            self.subjects = [dict(row) for row in cursor.fetchall()]
            
            # Load faculty
            cursor.execute('SELECT * FROM faculty')
            self.faculty = [dict(row) for row in cursor.fetchall()]
            
            # Initialize faculty load tracking
            for faculty in self.faculty:
                self.faculty_load[faculty['id']] = 0
            
            # Load available slots (non-break)
            cursor.execute('''
                SELECT * FROM timetable_slots 
                WHERE config_id = ? AND is_break = 0
                ORDER BY day, slot_number
            ''', (self.config_id,))
            self.available_slots = [dict(row) for row in cursor.fetchall()]
            
            # Build day-slot mapping
            for slot in self.available_slots:
                self.day_slot_map[slot['day']].append(slot['id'])
            
            # Load locations
            cursor.execute('SELECT * FROM locations ORDER BY room_type, capacity')
            self.locations = [dict(row) for row in cursor.fetchall()]
            
            return len(self.subjects) > 0 and len(self.faculty) > 0
            
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
        finally:
            conn.close()
    
    def get_subject_priority(self, subject: Dict) -> Tuple[int, int, int]:
        """
        Calculate priority for subject scheduling
        Returns: (total_hours, lab_hours, lecture_hours) for sorting
        Higher values = higher priority
        """
        total = subject['lecture_credits'] + subject['lab_credits']
        return (total, subject['lab_credits'], subject['lecture_credits'])
    
    def get_eligible_faculty(self, subject_id: int) -> List[int]:
        """
        Get faculty who can teach this subject
        TODO: Implement faculty_subject mapping
        For now, returns all faculty
        """
        return [f['id'] for f in self.faculty]
    
    def is_faculty_available(self, faculty_id: int, slot: Dict) -> Tuple[bool, str]:
        """Check if faculty is available for this slot"""
        faculty = next((f for f in self.faculty if f['id'] == faculty_id), None)
        if not faculty:
            return False, "Faculty not found"
        
        # Check day availability
        available_days = self._parse_availability(faculty['availability'])
        if slot['day'] not in available_days:
            return False, f"Faculty not available on {slot['day']}"
        
        # Check if already assigned at this time
        for scheduled_slot_id, assignment in self.schedule.items():
            if assignment['faculty_id'] == faculty_id:
                scheduled_slot = next((s for s in self.available_slots 
                                     if s['id'] == scheduled_slot_id), None)
                if scheduled_slot:
                    if (scheduled_slot['day'] == slot['day'] and 
                        scheduled_slot['start_time'] == slot['start_time']):
                        return False, "Faculty already scheduled at this time"
        
        # Check weekly hour limit
        if self.faculty_load[faculty_id] >= faculty['max_hours_per_week']:
            return False, "Faculty weekly hour limit reached"
        
        # Check consecutive hours limit
        if not self._check_consecutive_hours(faculty_id, slot):
            return False, f"Exceeds {self.max_consecutive_hours} consecutive hours limit"
        
        return True, "Available"
    
    def _parse_availability(self, availability_str: str) -> List[str]:
        """Parse availability string to full day names"""
        day_map = {
            'Mon': 'Monday', 'Tue': 'Tuesday', 'Wed': 'Wednesday',
            'Thu': 'Thursday', 'Fri': 'Friday', 'Sat': 'Saturday'
        }
        
        if '-' in availability_str:
            short_days = availability_str.split('-')
        elif ',' in availability_str:
            short_days = availability_str.split(',')
        else:
            short_days = [availability_str]
        
        return [day_map.get(d.strip(), d.strip()) for d in short_days]
    
    def _check_consecutive_hours(self, faculty_id: int, slot: Dict) -> bool:
        """Check if adding this slot exceeds consecutive hours limit"""
        day = slot['day']
        slot_number = slot['slot_number']
        
        # Get all slots assigned to this faculty on this day
        faculty_day_slots = []
        for scheduled_slot_id, assignment in self.schedule.items():
            if assignment['faculty_id'] == faculty_id:
                scheduled_slot = next((s for s in self.available_slots 
                                     if s['id'] == scheduled_slot_id), None)
                if scheduled_slot and scheduled_slot['day'] == day:
                    faculty_day_slots.append(scheduled_slot['slot_number'])
        
        faculty_day_slots.append(slot_number)
        faculty_day_slots.sort()
        
        # Check for consecutive sequence
        consecutive = 1
        for i in range(1, len(faculty_day_slots)):
            if faculty_day_slots[i] == faculty_day_slots[i-1] + 1:
                consecutive += 1
                if consecutive > self.max_consecutive_hours:
                    return False
            else:
                consecutive = 1
        
        return True
    
    def find_consecutive_slots(self, day: str, start_slot_number: int, 
                              count: int = 2) -> Optional[List[int]]:
        """Find consecutive available slots for labs"""
        slots = []
        
        for i in range(count):
            target_slot = next((s for s in self.available_slots 
                              if s['day'] == day and 
                              s['slot_number'] == start_slot_number + i), None)
            
            if not target_slot or target_slot['id'] in self.schedule:
                return None
            
            slots.append(target_slot['id'])
        
        return slots
    
    def assign_slot(self, slot_id: int, subject_id: int, faculty_id: int, 
                   slot_type: str = 'lecture'):
        """Assign a subject and faculty to a slot"""
        self.schedule[slot_id] = {
            'subject_id': subject_id,
            'faculty_id': faculty_id,
            'slot_type': slot_type
        }
        self.faculty_load[faculty_id] += 1
    
    def assign_room(self, slot_id: int, subject: Dict, slot_type: str):
        """
        Intelligently assign a room to a scheduled slot
        """
        # Determine required room type
        if slot_type == 'lab':
            required_type = 'Lab'
            min_capacity = 30
        else:
            required_type = 'Classroom'
            min_capacity = 50  # Default class size
        
        # Get slot details
        slot = next((s for s in self.available_slots if s['id'] == slot_id), None)
        if not slot:
            return None
        
        # Find available rooms of correct type
        suitable_rooms = [
            loc for loc in self.locations 
            if loc['room_type'] == required_type and 
            loc['capacity'] >= min_capacity
        ]
        
        # Check which rooms are available at this time
        for scheduled_slot_id, room_id in self.room_assignments.items():
            scheduled_slot = next((s for s in self.available_slots 
                                 if s['id'] == scheduled_slot_id), None)
            
            if scheduled_slot and scheduled_slot['day'] == slot['day']:
                if scheduled_slot['start_time'] == slot['start_time']:
                    # Remove occupied room from suitable list
                    suitable_rooms = [r for r in suitable_rooms if r['id'] != room_id]
        
        # Assign best available room
        if suitable_rooms:
            # Prefer rooms with capacity closest to requirement
            best_room = min(suitable_rooms, key=lambda r: abs(r['capacity'] - min_capacity))
            self.room_assignments[slot_id] = best_room['id']
            return best_room['id']
        
        self.warnings.append(f"No suitable room found for slot {slot_id}")
        return None
    
    def schedule_lectures(self, subject: Dict) -> Tuple[bool, int]:
        """Schedule lecture hours for a subject"""
        lecture_hours = subject['lecture_credits']
        if lecture_hours == 0:
            return True, 0
        
        eligible_faculty = self.get_eligible_faculty(subject['id'])
        if not eligible_faculty:
            return False, 0
        
        scheduled = 0
        attempts = 0
        max_attempts = len(self.available_slots) * 2
        days_used = set()
        
        # Try to distribute across different days
        while scheduled < lecture_hours and attempts < max_attempts:
            attempts += 1
            
            # Prefer days not yet used
            preferred_slots = [
                s for s in self.available_slots 
                if s['day'] not in days_used and s['id'] not in self.schedule
            ]
            
            if not preferred_slots:
                preferred_slots = [
                    s for s in self.available_slots 
                    if s['id'] not in self.schedule
                ]
            
            if not preferred_slots:
                break
            
            slot = random.choice(preferred_slots)
            
            # Try each eligible faculty
            for faculty_id in eligible_faculty:
                is_available, reason = self.is_faculty_available(faculty_id, slot)
                
                if is_available:
                    self.assign_slot(slot['id'], subject['id'], faculty_id, 'lecture')
                    self.assign_room(slot['id'], subject, 'lecture')
                    days_used.add(slot['day'])
                    scheduled += 1
                    break
        
        return scheduled == lecture_hours, scheduled
    
    def schedule_labs(self, subject: Dict) -> Tuple[bool, int]:
        """Schedule lab hours (requires consecutive slots)"""
        lab_hours = subject['lab_credits']
        if lab_hours == 0:
            return True, 0
        
        blocks_needed = (lab_hours + 1) // 2  # 2 hours per block
        eligible_faculty = self.get_eligible_faculty(subject['id'])
        
        if not eligible_faculty:
            return False, 0
        
        scheduled_blocks = 0
        days = list(set(s['day'] for s in self.available_slots))
        
        for day in days:
            if scheduled_blocks >= blocks_needed:
                break
            
            day_slots = sorted(
                [s for s in self.available_slots if s['day'] == day],
                key=lambda x: x['slot_number']
            )
            
            for slot in day_slots:
                if scheduled_blocks >= blocks_needed:
                    break
                
                consecutive_slots = self.find_consecutive_slots(day, slot['slot_number'], 2)
                
                if consecutive_slots:
                    for faculty_id in eligible_faculty:
                        # Check if faculty available for both slots
                        all_available = all(
                            self.is_faculty_available(
                                faculty_id, 
                                next(s for s in self.available_slots if s['id'] == sid)
                            )[0] 
                            for sid in consecutive_slots
                        )
                        
                        if all_available:
                            # Assign both slots
                            for sid in consecutive_slots:
                                self.assign_slot(sid, subject['id'], faculty_id, 'lab')
                                self.assign_room(sid, subject, 'lab')
                            
                            scheduled_blocks += 1
                            break
        
        return scheduled_blocks >= blocks_needed, scheduled_blocks
    
    def schedule_subject(self, subject: Dict) -> Dict:
        """Schedule both lectures and labs for a subject"""
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
        stats['labs_scheduled'] = lab_count * 2
        
        stats['success'] = lecture_success and lab_success
        
        return stats
    
    def generate_schedule(self) -> Tuple[bool, Dict]:
        """Main scheduling algorithm with optimization"""
        if not self.load_data():
            return False, {"error": "Failed to load data"}
        
        # Sort subjects by priority
        self.subjects.sort(
            key=lambda x: self.get_subject_priority(x),
            reverse=True
        )
        
        results = {
            'total_subjects': len(self.subjects),
            'successfully_scheduled': 0,
            'partially_scheduled': 0,
            'failed': 0,
            'details': []
        }
        
        # Schedule each subject
        for subject in self.subjects:
            stats = self.schedule_subject(subject)
            
            if stats['success']:
                results['successfully_scheduled'] += 1
            elif stats['lectures_scheduled'] > 0 or stats['labs_scheduled'] > 0:
                results['partially_scheduled'] += 1
            else:
                results['failed'] += 1
            
            results['details'].append(stats)
        
        # Detect conflicts
        self.detect_conflicts()
        results['conflicts'] = len(self.conflicts)
        results['warnings'] = len(self.warnings)
        
        return True, results
    
    def detect_conflicts(self):
        """Comprehensive conflict detection"""
        self.conflicts = []
        
        # Check faculty double-booking
        faculty_schedule = defaultdict(dict)
        
        for slot_id, assignment in self.schedule.items():
            slot = next((s for s in self.available_slots if s['id'] == slot_id), None)
            if not slot:
                continue
            
            faculty_id = assignment['faculty_id']
            time_key = f"{slot['day']}_{slot['start_time']}"
            
            if time_key in faculty_schedule[faculty_id]:
                self.conflicts.append({
                    'type': 'faculty_double_booking',
                    'faculty_id': faculty_id,
                    'day': slot['day'],
                    'time': slot['start_time'],
                    'slots': [faculty_schedule[faculty_id][time_key], slot_id]
                })
            else:
                faculty_schedule[faculty_id][time_key] = slot_id
        
        # Check room double-booking
        room_schedule = defaultdict(dict)
        
        for slot_id, room_id in self.room_assignments.items():
            slot = next((s for s in self.available_slots if s['id'] == slot_id), None)
            if not slot:
                continue
            
            time_key = f"{slot['day']}_{slot['start_time']}"
            
            if time_key in room_schedule[room_id]:
                self.conflicts.append({
                    'type': 'room_double_booking',
                    'room_id': room_id,
                    'day': slot['day'],
                    'time': slot['start_time'],
                    'slots': [room_schedule[room_id][time_key], slot_id]
                })
            else:
                room_schedule[room_id][time_key] = slot_id
    
    def save_schedule(self) -> Tuple[bool, str]:
        """Save generated schedule to database"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Update timetable slots
            for slot_id, assignment in self.schedule.items():
                room_id = self.room_assignments.get(slot_id)
                
                cursor.execute('''
                    UPDATE timetable_slots 
                    SET subject_id = ?, faculty_id = ?, slot_type = ?, room_id = ?
                    WHERE id = ?
                ''', (
                    assignment['subject_id'],
                    assignment['faculty_id'],
                    assignment['slot_type'],
                    room_id,
                    slot_id
                ))
            
            conn.commit()
            return True, "Schedule saved successfully"
        
        except Exception as e:
            conn.rollback()
            return False, f"Error saving schedule: {str(e)}"
        
        finally:
            conn.close()
    
    def get_optimization_score(self) -> Dict:
        """
        Calculate optimization metrics for the schedule
        """
        score = {
            'faculty_load_balance': self._calculate_load_balance(),
            'room_utilization': self._calculate_room_utilization(),
            'schedule_density': self._calculate_schedule_density(),
            'overall_score': 0.0
        }
        
        # Calculate weighted overall score
        score['overall_score'] = (
            score['faculty_load_balance'] * 0.4 +
            score['room_utilization'] * 0.3 +
            score['schedule_density'] * 0.3
        )
        
        return score
    
    def _calculate_load_balance(self) -> float:
        """Calculate how evenly workload is distributed among faculty"""
        if not self.faculty_load:
            return 0.0
        
        loads = list(self.faculty_load.values())
        avg_load = sum(loads) / len(loads)
        
        if avg_load == 0:
            return 0.0
        
        variance = sum((l - avg_load) ** 2 for l in loads) / len(loads)
        std_dev = variance ** 0.5
        
        # Lower std_dev = better balance (normalize to 0-1 scale)
        return max(0, 1 - (std_dev / avg_load))
    
    def _calculate_room_utilization(self) -> float:
        """Calculate room utilization percentage"""
        if not self.locations:
            return 0.0
        
        total_slots = len(self.available_slots)
        rooms_assigned = len(self.room_assignments)
        
        return rooms_assigned / total_slots if total_slots > 0 else 0.0
    
    def _calculate_schedule_density(self) -> float:
        """Calculate how efficiently slots are used"""
        total_slots = len(self.available_slots)
        assigned_slots = len(self.schedule)
        
        return assigned_slots / total_slots if total_slots > 0 else 0.0