#!/usr/bin/env python
"""
Sample data generator for testing the Attendance Tracker
"""

import os
import sys
import django
from datetime import datetime, timedelta
import random

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_tracker.settings')

# Setup Django
django.setup()

from django.contrib.auth.models import User
from tracker.models import Course, LectureSchedule, AttendanceRecord

def create_sample_data():
    """Create sample data for testing"""
    print("Creating sample data...")
    
    # Create a test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"Created test user: {user.username}")
    
    # Sample courses data
    courses_data = [
        {'name': 'Mathematics', 'total': 30, 'attended': 28},
        {'name': 'Physics', 'total': 25, 'attended': 18},
        {'name': 'Chemistry', 'total': 28, 'attended': 20},
        {'name': 'Computer Science', 'total': 32, 'attended': 30},
        {'name': 'English Literature', 'total': 20, 'attended': 14},
    ]
    
    # Create courses
    for course_data in courses_data:
        course, created = Course.objects.get_or_create(
            user=user,
            name=course_data['name'],
            defaults={
                'total_lectures': course_data['total'],
                'attended_lectures': course_data['attended']
            }
        )
        
        if created:
            print(f"Created course: {course.name} ({course.attendance_percentage}%)")
            
            # Create sample schedule
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
            day = random.choice(days)
            start_hour = random.randint(9, 15)
            
            schedule, _ = LectureSchedule.objects.get_or_create(
                course=course,
                day_of_week=day,
                start_time=f"{start_hour:02d}:00:00",
                defaults={
                    'end_time': f"{start_hour + 1:02d}:00:00"
                }
            )
            
            # Create sample attendance records
            start_date = datetime.now().date() - timedelta(days=course.total_lectures * 7)
            for i in range(course.total_lectures):
                record_date = start_date + timedelta(days=i * 7)
                attended = i < course.attended_lectures
                
                AttendanceRecord.objects.get_or_create(
                    course=course,
                    date=record_date,
                    defaults={
                        'attended': attended,
                        'notes': f"{'Present' if attended else 'Absent'} - Week {i + 1}"
                    }
                )
    
    print("Sample data creation complete!")
    print(f"Login with username: {user.username}, password: testpass123")

if __name__ == '__main__':
    create_sample_data()
