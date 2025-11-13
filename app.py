"""
Main Flask Application for Timetable Management System
COMPLETE VERSION WITH LOCATION MANAGEMENT
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
from werkzeug.utils import secure_filename

# Import services
from database.db_setup import initialize_database, get_table_info
from services.file_handler import (
    process_faculty_file, 
    process_subject_file,
    process_location_file,  # ADD THIS
    save_uploaded_file,
    UPLOAD_FOLDER
)
from services.data_service import (
    insert_faculty_data,
    insert_subject_data,
    get_all_faculty,
    get_all_subjects,
    get_subjects_by_semester,
    get_database_stats
)
from services.config_service import (
    save_academic_config,
    get_active_config,
    generate_time_slots,
    get_time_slots
)
from services.scheduler import TimetableScheduler
from services.timetable_service import (
    get_class_timetable_grid,
    get_class_timetable_multishift,
    get_faculty_timetable,
    get_faculty_timetable_grid,
    get_faculty_timetable_multishift,
    get_all_faculty_list,
    get_timetable_statistics
)
# ADD THESE IMPORTS FOR LOCATION MANAGEMENT
from services.location_service import (
    insert_location_data,
    get_all_locations,
    get_location_statistics,
    delete_location,
    get_locations_by_type,
    search_locations
)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize database on startup
initialize_database()

# ==================== HOME PAGE ====================
@app.route('/')
def index():
    """Landing page"""
    stats = get_database_stats()
    active_config = get_active_config()
    return render_template('index.html', stats=stats, config=active_config)

# ==================== FILE UPLOAD ====================
@app.route('/upload')
def upload_page():
    """Upload page"""
    return render_template('upload.html')

@app.route('/upload/faculty', methods=['POST'])
def upload_faculty():
    """Handle faculty file upload"""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('upload_page'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('upload_page'))
    
    # Save file
    success, filepath = save_uploaded_file(file)
    
    if not success:
        flash(filepath, 'error')
        return redirect(url_for('upload_page'))
    
    # Process file
    success, data, preview, warnings = process_faculty_file(filepath)
    
    if not success:
        flash(f'Error: {data}', 'error')
        return redirect(url_for('upload_page'))
    
    # Show warnings if any
    for warning in warnings:
        flash(warning, 'warning')
    
    # Insert into database
    success, message, stats = insert_faculty_data(data)
    
    if success:
        flash(f'Success! {message}', 'success')
    else:
        flash(f'Error: {message}', 'error')
    
    return redirect(url_for('upload_page'))

@app.route('/upload/subject', methods=['POST'])
def upload_subject():
    """Handle subject file upload"""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('upload_page'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('upload_page'))
    
    # Save file
    success, filepath = save_uploaded_file(file)
    
    if not success:
        flash(filepath, 'error')
        return redirect(url_for('upload_page'))
    
    # Process file
    success, data, preview, warnings = process_subject_file(filepath)
    
    if not success:
        flash(f'Error: {data}', 'error')
        return redirect(url_for('upload_page'))
    
    # Show warnings if any
    for warning in warnings:
        flash(warning, 'warning')
    
    # Insert into database
    success, message, stats = insert_subject_data(data)
    
    if success:
        flash(f'Success! {message}', 'success')
    else:
        flash(f'Error: {message}', 'error')
    
    return redirect(url_for('upload_page'))

# ==================== LOCATION MANAGEMENT (NEW SECTION) ====================
@app.route('/upload/location')
def upload_location_page():
    """Location upload page"""
    return render_template('upload_location.html')

@app.route('/upload/location', methods=['POST'])
def upload_location():
    """Handle location file upload"""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('upload_location_page'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('upload_location_page'))
    
    # Save file
    success, filepath = save_uploaded_file(file)
    
    if not success:
        flash(filepath, 'error')
        return redirect(url_for('upload_location_page'))
    
    # Process file
    success, data, preview, warnings = process_location_file(filepath)
    
    if not success:
        flash(f'Error: {data}', 'error')
        return redirect(url_for('upload_location_page'))
    
    # Show warnings if any
    for warning in warnings:
        flash(warning, 'warning')
    
    # Insert into database
    success, message, stats = insert_location_data(data)
    
    if success:
        flash(f'Success! {message}', 'success')
        return redirect(url_for('view_locations'))
    else:
        flash(f'Error: {message}', 'error')
        return redirect(url_for('upload_location_page'))

@app.route('/locations')
def view_locations():
    """View all locations page"""
    locations = get_all_locations()
    stats = get_location_statistics()
    
    return render_template('view_locations.html', 
                         locations=locations, 
                         stats=stats)

@app.route('/api/location/<int:location_id>/delete', methods=['POST'])
def delete_location_api(location_id):
    """API endpoint to delete a location"""
    success, message = delete_location(location_id)
    return jsonify({'success': success, 'message': message})

@app.route('/api/locations')
def api_locations():
    """API endpoint for all locations"""
    locations = get_all_locations()
    return jsonify(locations)

@app.route('/api/locations/type/<room_type>')
def api_locations_by_type(room_type):
    """API endpoint for locations by type"""
    locations = get_locations_by_type(room_type)
    return jsonify(locations)

@app.route('/api/locations/search')
def api_locations_search():
    """API endpoint to search locations"""
    query = request.args.get('q', '')
    if query:
        locations = search_locations(query)
    else:
        locations = get_all_locations()
    return jsonify(locations)

@app.route('/api/locations/stats')
def api_location_stats():
    """API endpoint for location statistics"""
    stats = get_location_statistics()
    return jsonify(stats)

# ==================== CONFIGURATION ====================
@app.route('/configure')
def configure_page():
    """Configuration page"""
    stats = get_database_stats()
    active_config = get_active_config()
    return render_template('configure.html', stats=stats, config=active_config)

@app.route('/configure/save', methods=['POST'])
def save_configuration():
    """Save academic configuration"""
    academic_year = request.form.get('academic_year')
    term = request.form.get('term')
    semester = request.form.get('semester')
    working_days = request.form.get('working_days')
    shift_mode = request.form.get('shift_mode')
    
    # Parse shift timings based on mode
    if shift_mode == 'single':
        shift_timings = {
            'start': request.form.get('single_start'),
            'end': request.form.get('single_end')
        }
    else:
        # Multi-shift (for simplicity, using preset shifts)
        shift_timings = [
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
    
    # Save configuration
    success, message, config_id = save_academic_config(
        academic_year, term, semester, working_days, shift_mode, shift_timings
    )
    
    if success:
        # Generate time slots
        slot_success, slot_message, count = generate_time_slots(config_id)
        
        if slot_success:
            flash(f'Configuration saved! {count} time slots generated.', 'success')
        else:
            flash(f'Configuration saved but slot generation failed: {slot_message}', 'warning')
    else:
        flash(f'Error: {message}', 'error')
    
    return redirect(url_for('configure_page'))

# ==================== GENERATE TIMETABLE ====================
@app.route('/generate')
def generate_page():
    """Generate timetable page"""
    active_config = get_active_config()
    
    if not active_config:
        flash('Please configure academic settings first', 'error')
        return redirect(url_for('configure_page'))
    
    subjects = get_subjects_by_semester(active_config['semester'])
    
    return render_template('generate.html', config=active_config, subjects=subjects)

@app.route('/generate/run', methods=['POST'])
def run_generation():
    """Run timetable generation"""
    active_config = get_active_config()
    
    if not active_config:
        flash('Please configure academic settings first', 'error')
        return redirect(url_for('configure_page'))
    
    # Initialize scheduler
    scheduler = TimetableScheduler(active_config['id'], active_config['semester'])
    
    # Load data
    if not scheduler.load_data():
        flash('No subjects found for this semester', 'error')
        return redirect(url_for('generate_page'))
    
    # Generate schedule
    success, results = scheduler.generate_schedule()
    
    if success:
        # Check conflicts
        conflicts = scheduler.get_conflicts()
        
        if conflicts:
            flash(f'Schedule generated with {len(conflicts)} conflicts. Please review.', 'warning')
        else:
            flash('Schedule generated successfully with no conflicts!', 'success')
        
        # Save to database
        save_success, save_message = scheduler.save_schedule()
        
        if not save_success:
            flash(f'Warning: {save_message}', 'warning')
        
        # Show results
        flash(f'Scheduled: {results["successfully_scheduled"]}/{results["total_subjects"]} subjects', 'info')
        
        return redirect(url_for('view_timetable'))
    else:
        flash(f'Generation failed: {results.get("error", "Unknown error")}', 'error')
        return redirect(url_for('generate_page'))

# ==================== VIEW TIMETABLE ====================
@app.route('/timetable')
def view_timetable():
    """View timetable page"""
    active_config = get_active_config()
    
    if not active_config:
        flash('Please configure academic settings first', 'error')
        return redirect(url_for('configure_page'))
    
    view_type = request.args.get('type', 'class')
    
    if view_type == 'class':
        # Check if multi-shift
        if active_config['shift_mode'] == 'multi':
            timetable_data = get_class_timetable_multishift(active_config['id'])
        else:
            timetable_data = get_class_timetable_grid(active_config['id'])
        
        if not timetable_data:
            flash('No timetable data found', 'error')
            return redirect(url_for('generate_page'))
        
        stats = get_timetable_statistics(active_config['id'])
        
        # Check if multi-shift
        if timetable_data.get('is_multi_shift'):
            return render_template('timetable_class.html', 
                                 config=timetable_data['config'], 
                                 days=timetable_data['days'],
                                 shifts=timetable_data['shifts'],
                                 is_multi_shift=True,
                                 stats=stats)
        else:
            return render_template('timetable_class.html', 
                                 config=timetable_data['config'], 
                                 days=timetable_data['days'],
                                 time_slots=timetable_data['time_slots'],
                                 is_multi_shift=False,
                                 stats=stats)
    
    else:  # Faculty view
        # Get all faculty for dropdown
        all_faculty = get_all_faculty_list()
        
        if not all_faculty:
            flash('No faculty found. Please upload faculty data first.', 'error')
            return redirect(url_for('upload_page'))
        
        # Get selected faculty ID from query parameter
        faculty_id = request.args.get('faculty_id')
        
        # If no faculty selected, use the first one
        if not faculty_id:
            faculty_id = all_faculty[0]['id']
        else:
            faculty_id = int(faculty_id)
        
        # Check if multi-shift
        if active_config['shift_mode'] == 'multi':
            timetable_data = get_faculty_timetable_multishift(active_config['id'], faculty_id)
        else:
            timetable_data = get_faculty_timetable_grid(active_config['id'], faculty_id)
        
        if not timetable_data:
            flash('No timetable data found for this faculty', 'warning')
            return redirect(url_for('generate_page'))
        
        # Check if multi-shift
        if timetable_data.get('is_multi_shift'):
            return render_template('timetable_faculty_grid.html',
                                 config=timetable_data['config'],
                                 faculty=timetable_data['faculty'],
                                 days=timetable_data['days'],
                                 shifts=timetable_data['shifts'],
                                 is_multi_shift=True,
                                 total_hours=timetable_data['total_hours'],
                                 all_faculty=all_faculty)
        else:
            return render_template('timetable_faculty_grid.html',
                                 config=timetable_data['config'],
                                 faculty=timetable_data['faculty'],
                                 days=timetable_data['days'],
                                 time_slots=timetable_data['time_slots'],
                                 is_multi_shift=False,
                                 total_hours=timetable_data['total_hours'],
                                 all_faculty=all_faculty)

# ==================== API ENDPOINTS ====================
@app.route('/api/stats')
def api_stats():
    """API endpoint for database statistics"""
    stats = get_database_stats()
    return jsonify(stats)

@app.route('/api/subjects/<int:semester>')
def api_subjects(semester):
    """API endpoint for subjects by semester"""
    subjects = get_subjects_by_semester(semester)
    return jsonify(subjects)

# ==================== ERROR HANDLERS ====================
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error="Internal server error"), 500

# ==================== RUN APPLICATION ====================
if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  TIMETABLE MANAGEMENT SYSTEM")
    print("=" * 60)
    print("\n🚀 Starting Flask server...")
    print("📱 Open your browser and go to: http://127.0.0.1:5000")
    print("⏹️  Press CTRL+C to stop the server\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)