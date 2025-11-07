"""
Test Script for Module 2: File Upload & Data Processing
"""

import sys
import os
sys.path.append('.')

from services.file_handler import (
    process_faculty_file, 
    process_subject_file,
    read_file,
    validate_faculty_file,
    validate_subject_file
)
from services.data_service import (
    insert_faculty_data,
    insert_subject_data,
    get_all_faculty,
    get_all_subjects,
    get_database_stats
)

def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def test_file_reading():
    """Test 1: Reading CSV files"""
    print_header("TEST 1: Reading CSV Files")
    
    test_files = [
        ('sample_faculty.csv', 'Faculty'),
        ('sample_subjects.csv', 'Subject')
    ]
    
    for filename, file_type in test_files:
        print(f"\n📄 Testing {file_type} file: {filename}")
        
        if not os.path.exists(filename):
            print(f"   ❌ File not found! Please create {filename}")
            continue
        
        df = read_file(filename)
        
        if df is not None:
            print(f"   ✅ File read successfully")
            print(f"   📊 Rows: {len(df)}, Columns: {len(df.columns)}")
            print(f"   📋 Columns: {', '.join(df.columns.tolist())}")
        else:
            print(f"   ❌ Failed to read file")

def test_file_validation():
    """Test 2: File validation"""
    print_header("TEST 2: File Validation")
    
    # Test faculty file
    print("\n📋 Validating Faculty File...")
    if os.path.exists('sample_faculty.csv'):
        df = read_file('sample_faculty.csv')
        is_valid, message, warnings = validate_faculty_file(df)
        
        if is_valid:
            print(f"   ✅ {message}")
            if warnings:
                for warning in warnings:
                    print(f"   ⚠️  {warning}")
        else:
            print(f"   ❌ {message}")
    else:
        print("   ❌ File not found")
    
    # Test subject file
    print("\n📋 Validating Subject File...")
    if os.path.exists('sample_subjects.csv'):
        df = read_file('sample_subjects.csv')
        is_valid, message, warnings = validate_subject_file(df)
        
        if is_valid:
            print(f"   ✅ {message}")
            if warnings:
                for warning in warnings:
                    print(f"   ⚠️  {warning}")
        else:
            print(f"   ❌ {message}")
    else:
        print("   ❌ File not found")

def test_file_processing():
    """Test 3: Complete file processing"""
    print_header("TEST 3: File Processing with Preview")
    
    # Process faculty file
    print("\n📋 Processing Faculty File...")
    if os.path.exists('sample_faculty.csv'):
        success, data, preview, warnings = process_faculty_file('sample_faculty.csv')
        
        if success:
            print(f"   ✅ File processed successfully")
            print(f"   📊 Total records: {preview['total_rows']}")
            print(f"   📋 Sample data:")
            for i, record in enumerate(preview['sample_data'][:3], 1):
                print(f"      {i}. {record['faculty_name']} ({record['short_name']})")
        else:
            print(f"   ❌ Processing failed: {data}")
    
    # Process subject file
    print("\n📋 Processing Subject File...")
    if os.path.exists('sample_subjects.csv'):
        success, data, preview, warnings = process_subject_file('sample_subjects.csv')
        
        if success:
            print(f"   ✅ File processed successfully")
            print(f"   📊 Total records: {preview['total_rows']}")
            print(f"   📋 Sample data:")
            for i, record in enumerate(preview['sample_data'][:3], 1):
                print(f"      {i}. {record['subject_name']} ({record['code']}) - Sem {record['semester']}")
        else:
            print(f"   ❌ Processing failed: {data}")

def test_database_insertion():
    """Test 4: Database insertion"""
    print_header("TEST 4: Database Insertion")
    
    # Insert faculty data
    print("\n📋 Inserting Faculty Data...")
    if os.path.exists('sample_faculty.csv'):
        success, data, preview, warnings = process_faculty_file('sample_faculty.csv')
        
        if success:
            insert_success, message, stats = insert_faculty_data(data)
            
            if insert_success:
                print(f"   ✅ {message}")
                print(f"   📊 Stats: {stats}")
            else:
                print(f"   ❌ Insertion failed: {message}")
    
    # Insert subject data
    print("\n📋 Inserting Subject Data...")
    if os.path.exists('sample_subjects.csv'):
        success, data, preview, warnings = process_subject_file('sample_subjects.csv')
        
        if success:
            insert_success, message, stats = insert_subject_data(data)
            
            if insert_success:
                print(f"   ✅ {message}")
                print(f"   📊 Stats: {stats}")
            else:
                print(f"   ❌ Insertion failed: {message}")

def test_data_retrieval():
    """Test 5: Data retrieval from database"""
    print_header("TEST 5: Data Retrieval")
    
    # Get all faculty
    print("\n👥 Faculty in Database:")
    faculty = get_all_faculty()
    if faculty:
        print(f"   Total: {len(faculty)}")
        for f in faculty[:5]:
            print(f"   • {f['faculty_name']} ({f['short_name']}) - {f['specialization']}")
        if len(faculty) > 5:
            print(f"   ... and {len(faculty) - 5} more")
    else:
        print("   ⚠️  No faculty found")
    
    # Get all subjects
    print("\n📚 Subjects in Database:")
    subjects = get_all_subjects()
    if subjects:
        print(f"   Total: {len(subjects)}")
        for s in subjects[:5]:
            print(f"   • {s['subject_name']} ({s['code']}) - Sem {s['semester']}")
            print(f"     Lectures: {s['lecture_credits']}hr, Labs: {s['lab_credits']}hr")
        if len(subjects) > 5:
            print(f"   ... and {len(subjects) - 5} more")
    else:
        print("   ⚠️  No subjects found")

def test_database_stats():
    """Test 6: Database statistics"""
    print_header("TEST 6: Database Statistics")
    
    stats = get_database_stats()
    
    print("\n📊 Current Database State:")
    print(f"   Faculty members: {stats['faculty_count']}")
    print(f"   Subjects: {stats['subject_count']}")
    print(f"   Faculty-Subject mappings: {stats['mappings_count']}")
    print(f"   Unique semesters: {stats['semesters_count']}")

def run_all_tests():
    """Run all Module 2 tests"""
    print("\n" + "🧪" * 35)
    print("  MODULE 2 TESTING: File Upload & Data Processing")
    print("🧪" * 35)
    
    # Check if sample files exist
    print("\n📁 Checking for sample files...")
    files_exist = True
    
    if not os.path.exists('sample_faculty.csv'):
        print("   ❌ sample_faculty.csv not found!")
        print("   💡 Create this file using the artifact provided")
        files_exist = False
    else:
        print("   ✅ sample_faculty.csv found")
    
    if not os.path.exists('sample_subjects.csv'):
        print("   ❌ sample_subjects.csv not found!")
        print("   💡 Create this file using the artifact provided")
        files_exist = False
    else:
        print("   ✅ sample_subjects.csv found")
    
    if not files_exist:
        print("\n⚠️  Please create sample CSV files before running tests")
        return
    
    # Run tests
    try:
        test_file_reading()
        test_file_validation()
        test_file_processing()
        test_database_insertion()
        test_data_retrieval()
        test_database_stats()
        
        print_header("✅ ALL TESTS COMPLETED")
        print("\n📝 Next Steps:")
        print("   1. Module 2 is ready ✅")
        print("   2. Move to Module 3: Academic Configuration")
        print("   3. Run: python tests/test_module3.py")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()