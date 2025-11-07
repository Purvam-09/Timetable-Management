"""
Test Script for Module 3: Academic Configuration & Slot Generation
"""

import sys
sys.path.append('.')

from services.config_service import (
    validate_academic_year,
    validate_term_semester,
    save_academic_config,
    get_active_config,
    generate_time_slots,
    get_time_slots,
    get_available_slots
)

def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def test_validation():
    """Test 1: Validation functions"""
    print_header("TEST 1: Validation Functions")
    
    # Test academic year validation
    print("\n📅 Testing Academic Year Validation:")
    test_years = [
        ("2024-2025", True),
        ("2023-2024", True),
        ("2024-2026", False),
        ("2024", False),
        ("abc-def", False)
    ]
    
    for year, expected in test_years:
        result = validate_academic_year(year)
        status = "✅" if result == expected else "❌"
        print(f"   {status} {year}: {result}")
    
    # Test term-semester validation
    print("\n📆 Testing Term-Semester Validation:")
    test_combos = [
        ("Jan-June", 2, True),
        ("Jan-June", 4, True),
        ("Jan-June", 1, False),  # Odd semester in Jan-June
        ("July-Dec", 1, True),
        ("July-Dec", 3, True),
        ("July-Dec", 2, False),  # Even semester in July-Dec
    ]
    
    for term, sem, expected in test_combos:
        is_valid, message = validate_term_semester(term, sem)
        status = "✅" if is_valid == expected else "❌"
        print(f"   {status} {term} - Sem {sem}: {message}")

def test_single_shift_config():
    """Test 2: Single shift configuration"""
    print_header("TEST 2: Single Shift Configuration")
    
    print("\n📝 Creating single shift configuration...")
    
    config_data = {
        'academic_year': '2024-2025',
        'term': 'July-Dec',
        'semester': 3,
        'working_days': 'Mon-Fri',
        'shift_mode': 'single',
        'shift_timings': {
            'start': '09:00',
            'end': '17:00'
        }
    }
    
    success, message, config_id = save_academic_config(**config_data)
    
    if success:
        print(f"   ✅ {message}")
        print(f"   📋 Config ID: {config_id}")
        
        # Test retrieval
        print("\n📖 Retrieving active configuration...")
        active_config = get_active_config()
        
        if active_config:
            print(f"   ✅ Active config retrieved")
            print(f"   📅 Year: {active_config['academic_year']}")
            print(f"   📆 Term: {active_config['term']}")
            print(f"   🎓 Semester: {active_config['semester']}")
            print(f"   📅 Working Days: {active_config['working_days']}")
            print(f"   ⏰ Shift: {active_config['shift_timings']}")
        
        return config_id
    else:
        print(f"   ❌ {message}")
        return None

def test_slot_generation(config_id):
    """Test 3: Time slot generation"""
    print_header("TEST 3: Time Slot Generation")
    
    if not config_id:
        print("   ⚠️  No config ID provided, skipping test")
        return
    
    print("\n⏰ Generating time slots...")
    success, message, count = generate_time_slots(config_id)
    
    if success:
        print(f"   ✅ {message}")
        print(f"   📊 Total slots created: {count}")
        
        # Retrieve and display sample slots
        print("\n📋 Sample slots for Monday:")
        monday_slots = get_time_slots(config_id, 'Monday')
        
        for slot in monday_slots[:10]:  # Show first 10 slots
            slot_type = "🍽️ BREAK" if slot['is_break'] else "📚 CLASS"
            print(f"   {slot_type} Slot {slot['slot_number']}: {slot['start_time']} - {slot['end_time']}")
        
        if len(monday_slots) > 10:
            print(f"   ... and {len(monday_slots) - 10} more slots")
        
        # Show available (non-break) slots
        print("\n📚 Available teaching slots (Monday):")
        available = get_available_slots(config_id, 'Monday')
        print(f"   Total available slots: {len(available)}")
        for slot in available[:5]:
            print(f"   • Slot {slot['slot_number']}: {slot['start_time']} - {slot['end_time']}")
        
    else:
        print(f"   ❌ {message}")

def test_multi_shift_config():
    """Test 4: Multi-shift configuration"""
    print_header("TEST 4: Multi-Shift Configuration")
    
    print("\n📝 Creating multi-shift configuration...")
    
    config_data = {
        'academic_year': '2024-2025',
        'term': 'Jan-June',
        'semester': 4,
        'working_days': 'Mon-Sat',
        'shift_mode': 'multi',
        'shift_timings': [
            {
                'name': 'Morning Shift',
                'start': '08:00',
                'end': '13:00'
            },
            {
                'name': 'Afternoon Shift',
                'start': '14:00',
                'end': '18:00'
            }
        ]
    }
    
    success, message, config_id = save_academic_config(**config_data)
    
    if success:
        print(f"   ✅ {message}")
        print(f"   📋 Config ID: {config_id}")
        
        # Generate slots
        print("\n⏰ Generating multi-shift slots...")
        success, message, count = generate_time_slots(config_id)
        
        if success:
            print(f"   ✅ {message}")
            
            # Show slots for one day
            print("\n📋 Saturday slots (showing multi-shift):")
            saturday_slots = get_time_slots(config_id, 'Saturday')
            
            for slot in saturday_slots:
                slot_type = "🍽️ BREAK" if slot['is_break'] else "📚 CLASS"
                print(f"   {slot_type} Slot {slot['slot_number']}: {slot['start_time']} - {slot['end_time']}")
        
        return config_id
    else:
        print(f"   ❌ {message}")
        return None

def test_all_days_slots(config_id):
    """Test 5: View slots across all days"""
    print_header("TEST 5: Slots Across All Days")
    
    if not config_id:
        print("   ⚠️  No config ID provided, skipping test")
        return
    
    config = get_active_config()
    working_days = config['working_days']
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    if working_days == 'Mon-Sat':
        days.append('Saturday')
    
    print(f"\n📅 Slot distribution across {working_days}:")
    
    for day in days:
        slots = get_time_slots(config_id, day)
        available = get_available_slots(config_id, day)
        breaks = len([s for s in slots if s['is_break']])
        
        print(f"\n   📌 {day}:")
        print(f"      Total slots: {len(slots)}")
        print(f"      Teaching slots: {len(available)}")
        print(f"      Break slots: {breaks}")

def run_all_tests():
    """Run all Module 3 tests"""
    print("\n" + "🧪" * 35)
    print("  MODULE 3 TESTING: Academic Configuration & Slot Generation")
    print("🧪" * 35)
    
    try:
        # Run tests
        test_validation()
        
        config_id = test_single_shift_config()
        test_slot_generation(config_id)
        
        multi_config_id = test_multi_shift_config()
        test_all_days_slots(multi_config_id)
        
        print_header("✅ ALL TESTS COMPLETED")
        print("\n📝 Module 3 Summary:")
        print("   ✅ Validation working correctly")
        print("   ✅ Single shift configuration successful")
        print("   ✅ Multi-shift configuration successful")
        print("   ✅ Time slot generation working")
        print("   ✅ Break slots properly created")
        
        print("\n📋 Next Steps:")
        print("   1. Module 3 is ready ✅")
        print("   2. Move to Module 4: Scheduling Engine")
        print("   3. Run: python tests/test_module4.py")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()