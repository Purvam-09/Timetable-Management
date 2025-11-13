# CSV/Excel processing

"""
File Handler Service
Handles CSV/Excel file uploads, validation, and preview
"""

import pandas as pd
import os
from werkzeug.utils import secure_filename

# Allowed file extensions
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
UPLOAD_FOLDER = 'uploads'

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_upload_folder():
    """Ensure upload folder exists"""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def read_file(filepath):
    """
    Read CSV or Excel file and return DataFrame
    
    Args:
        filepath: Path to the file
        
    Returns:
        pandas DataFrame or None if error
    """
    try:
        file_extension = filepath.rsplit('.', 1)[1].lower()
        
        if file_extension == 'csv':
            # Read CSV with common encoding issues handled
            try:
                df = pd.read_csv(filepath, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(filepath, encoding='latin-1')
        
        elif file_extension in ['xlsx', 'xls']:
            # Read Excel file
            df = pd.read_excel(filepath, engine='openpyxl' if file_extension == 'xlsx' else None)
        
        else:
            return None
        
        # Strip whitespace from column names (IMPORTANT!)
        df.columns = df.columns.str.strip()
        
        # Strip whitespace from string columns
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip() if df[col].dtype == 'object' else df[col]
        
        return df
    
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

def validate_faculty_file(df):
    """
    Validate faculty data file
    
    Required columns:
    - faculty_name
    - short_name
    - specialization (optional)
    - availability (optional)
    
    Returns:
        (is_valid, error_message, warnings)
    """
    required_columns = ['faculty_name', 'short_name']
    optional_columns = ['specialization', 'availability', 'max_hours_per_week']
    
    # Check if DataFrame is valid
    if df is None or df.empty:
        return False, "File is empty or could not be read", []
    
    # Check required columns
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}", []
    
    # Check for empty values in required columns
    for col in required_columns:
        if df[col].isnull().any():
            return False, f"Column '{col}' contains empty values", []
    
    # Check for duplicate short_names
    duplicates = df[df.duplicated(subset=['short_name'], keep=False)]
    if not duplicates.empty:
        dup_names = duplicates['short_name'].unique().tolist()
        return False, f"Duplicate short_name found: {', '.join(dup_names)}", []
    
    # Warnings for optional columns
    warnings = []
    for col in optional_columns:
        if col not in df.columns:
            warnings.append(f"Optional column '{col}' not found - will use defaults")
    
    return True, "Faculty file is valid", warnings

def validate_subject_file(df):
    """
    Validate subject data file
    
    Required columns:
    - subject_name
    - code
    - semester
    - lecture_credits
    - lab_credits
    
    Returns:
        (is_valid, error_message, warnings)
    """
    required_columns = ['subject_name', 'code', 'semester', 'lecture_credits', 'lab_credits']
    
    # Check if DataFrame is valid
    if df is None or df.empty:
        return False, "File is empty or could not be read", []
    
    # Check required columns
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}", []
    
    # Check for empty values in required columns
    for col in required_columns:
        if df[col].isnull().any():
            return False, f"Column '{col}' contains empty values", []
    
    # Check if semester is numeric
    try:
        df['semester'] = pd.to_numeric(df['semester'])
        if not df['semester'].between(1, 8).all():
            return False, "Semester must be between 1 and 8", []
    except:
        return False, "Semester must be a valid number", []
    
    # Check if credits are numeric
    try:
        df['lecture_credits'] = pd.to_numeric(df['lecture_credits'])
        df['lab_credits'] = pd.to_numeric(df['lab_credits'])
    except:
        return False, "Credits must be valid numbers", []
    
    # Check for negative credits
    if (df['lecture_credits'] < 0).any() or (df['lab_credits'] < 0).any():
        return False, "Credits cannot be negative", []
    
    # Check for duplicate codes
    duplicates = df[df.duplicated(subset=['code'], keep=False)]
    if not duplicates.empty:
        dup_codes = duplicates['code'].unique().tolist()
        return False, f"Duplicate subject codes found: {', '.join(dup_codes)}", []
    
    # Warnings
    warnings = []
    
    # Check if both credits are zero
    zero_credits = df[(df['lecture_credits'] == 0) & (df['lab_credits'] == 0)]
    if not zero_credits.empty:
        warnings.append(f"{len(zero_credits)} subject(s) have zero credits")
    
    return True, "Subject file is valid", warnings


def validate_location_file(df):
    """Validate location/classroom data file"""
    required_columns = ['room_number']
    optional_columns = ['building', 'floor', 'room_type', 'capacity']
    
    if df is None or df.empty:
        return False, "File is empty or could not be read", []
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}", []
    
    for col in required_columns:
        if df[col].isnull().any():
            return False, f"Column '{col}' contains empty values", []
    
    duplicates = df[df.duplicated(subset=['room_number'], keep=False)]
    if not duplicates.empty:
        dup_rooms = duplicates['room_number'].unique().tolist()
        return False, f"Duplicate room_number found: {', '.join(map(str, dup_rooms))}", []
    
    if 'floor' in df.columns:
        try:
            df['floor'] = pd.to_numeric(df['floor'])
        except:
            return False, "Floor must be a valid number", []
    
    if 'capacity' in df.columns:
        try:
            df['capacity'] = pd.to_numeric(df['capacity'])
            if (df['capacity'] < 0).any():
                return False, "Capacity cannot be negative", []
        except:
            return False, "Capacity must be a valid number", []
    
    warnings = []
    for col in optional_columns:
        if col not in df.columns:
            warnings.append(f"Optional column '{col}' not found - will use defaults")
    
    return True, "Location file is valid", warnings

def process_location_file(filepath):
    """Complete processing of location file"""
    df = read_file(filepath)
    
    if df is None:
        return False, "Could not read file", None, []
    
    is_valid, message, warnings = validate_location_file(df)
    
    if not is_valid:
        return False, message, None, warnings
    
    if 'building' not in df.columns:
        df['building'] = 'Main'
    
    if 'floor' not in df.columns:
        df['floor'] = 0
    
    if 'room_type' not in df.columns:
        df['room_type'] = 'Classroom'
    
    if 'capacity' not in df.columns:
        df['capacity'] = 60
    
    preview = get_file_preview(df)
    
    return True, df, preview, warnings

def get_file_preview(df, max_rows=10):
    """
    Get preview of DataFrame
    
    Returns:
        Dictionary with preview information
    """
    if df is None or df.empty:
        return None
    
    preview = {
        'total_rows': len(df),
        'total_columns': len(df.columns),
        'columns': df.columns.tolist(),
        'sample_data': df.head(max_rows).to_dict('records'),
        'data_types': df.dtypes.astype(str).to_dict()
    }
    
    return preview

def save_uploaded_file(file):
    """
    Save uploaded file to uploads folder
    
    Args:
        file: FileStorage object from Flask
        
    Returns:
        (success, filepath_or_error)
    """
    try:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            create_upload_folder()
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            return True, filepath
        else:
            return False, "Invalid file type. Only CSV, XLSX, XLS allowed."
    
    except Exception as e:
        return False, f"Error saving file: {str(e)}"

def process_faculty_file(filepath):
    """
    Complete processing of faculty file
    
    Returns:
        (success, data_or_error, preview, warnings)
    """
    # Read file
    df = read_file(filepath)
    
    if df is None:
        return False, "Could not read file", None, []
    
    # Validate
    is_valid, message, warnings = validate_faculty_file(df)
    
    if not is_valid:
        return False, message, None, warnings
    
    # Add default values for optional columns
    if 'specialization' not in df.columns:
        df['specialization'] = 'General'
    
    if 'availability' not in df.columns:
        df['availability'] = 'Mon,Tue,Wed,Thu,Fri,Sat'
    
    if 'max_hours_per_week' not in df.columns:
        df['max_hours_per_week'] = 24
    
    # Get preview
    preview = get_file_preview(df)
    
    return True, df, preview, warnings

def process_subject_file(filepath):
    """
    Complete processing of subject file
    
    Returns:
        (success, data_or_error, preview, warnings)
    """
    # Read file
    df = read_file(filepath)
    
    if df is None:
        return False, "Could not read file", None, []
    
    # Validate
    is_valid, message, warnings = validate_subject_file(df)
    
    if not is_valid:
        return False, message, None, warnings
    
    # Get preview
    preview = get_file_preview(df)
    
    return True, df, preview, warnings
