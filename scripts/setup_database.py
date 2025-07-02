#!/usr/bin/env python
"""
Database setup script for the Attendance Tracker
Run this script to create the database and apply migrations
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_tracker.settings')

# Setup Django
django.setup()

def setup_database():
    """Create database and apply migrations"""
    print("Setting up database...")
    
    # Make migrations for the tracker app specifically
    print("Creating migrations for tracker app...")
    execute_from_command_line(['manage.py', 'makemigrations', 'tracker'])
    
    # Apply migrations
    print("Applying migrations...")
    execute_from_command_line(['manage.py', 'migrate'])
    
    print("Database setup complete!")
    
    # Create superuser prompt
    create_superuser = input("Would you like to create a superuser? (y/n): ")
    if create_superuser.lower() == 'y':
        execute_from_command_line(['manage.py', 'createsuperuser'])

if __name__ == '__main__':
    setup_database()
