"""
Initialize the medical school test database
Creates SQLite database and executes all schema and data SQL statements
"""

import subprocess
import os
from pathlib import Path

def init_database(db_path='data/test_medical.db', schema_path='data/schema.sql', data_path='data/test_data.sql'):
    """
    Initialize the database with schema and test data
    
    Args:
        db_path: Path to the SQLite database file
        schema_path: Path to the schema SQL file
        data_path: Path to the test data SQL file
    """
    # Remove existing database if it exists
    if os.path.exists(db_path):
        print(f"Removing existing database: {db_path}")
        os.remove(db_path)
    
    print(f"Creating new database: {db_path}")
    
    try:
        # Execute schema SQL using sqlite3 command-line tool
        print(f"Executing schema from: {schema_path}")
        with open(schema_path, 'r', encoding='utf-8') as schema_file:
            result = subprocess.run(
                ['sqlite3', db_path],
                stdin=schema_file,
                capture_output=True,
                text=True
            )
        
        if result.returncode != 0:
            print(f"Error executing schema: {result.stderr}")
            raise Exception("Schema execution failed")
        
        print("Schema created successfully.")
        
        # Execute test data SQL
        print(f"Executing test data from: {data_path}")
        with open(data_path, 'r', encoding='utf-8') as data_file:
            result = subprocess.run(
                ['sqlite3', db_path],
                stdin=data_file,
                capture_output=True,
                text=True
            )
        
        if result.returncode != 0:
            print(f"Error executing test data: {result.stderr}")
            raise Exception("Test data insertion failed")
        
        print("Test data inserted successfully.")
        
        # Verify database
        print("\nVerifying database...")
        result = subprocess.run(
            ['sqlite3', db_path, "SELECT COUNT(*) FROM sqlite_master WHERE type='table';"],
            capture_output=True,
            text=True
        )
        table_count = int(result.stdout.strip())
        print(f"Total tables created: {table_count}")
        
        # Show sample counts
        print("\nSample record counts:")
        sample_tables = ['students', 'faculty', 'courses', 'departments', 'programs', 
                        'student_enrollments', 'exams', 'attendance_records']
        
        for table in sample_tables:
            result = subprocess.run(
                ['sqlite3', db_path, f"SELECT COUNT(*) FROM {table};"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                count = result.stdout.strip()
                print(f"  {table}: {count} records")
        
        print(f"\nDatabase initialization completed successfully!")
        print(f"Database file: {os.path.abspath(db_path)}")
        
    except Exception as e:
        print(f"Error during database initialization: {e}")
        raise

if __name__ == '__main__':
    # Get the script directory
    script_dir = Path(__file__).parent
    
    # Set paths relative to script directory
    db_path = script_dir / 'test_medical.db'
    schema_path = script_dir / 'schema.sql'
    data_path = script_dir / 'test_data.sql'
    
    init_database(str(db_path), str(schema_path), str(data_path))
