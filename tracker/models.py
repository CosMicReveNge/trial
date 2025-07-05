from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import datetime, timedelta, date
import math

class Course(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    total_lectures = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    attended_lectures = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'name']

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    @property
    def attendance_percentage(self):
        if self.total_lectures == 0:
            return 0
        return round((self.attended_lectures / self.total_lectures) * 100, 2)

    @property
    def is_below_threshold(self):
        return self.attendance_percentage < 75

    def lectures_needed_for_75_percent(self):
        """Calculate how many lectures need to be attended to reach 75%"""
        if self.attendance_percentage >= 75:
            return 0
        
        current_total = self.total_lectures
        current_attended = self.attended_lectures
        
        if current_total == 0:
            return 1
            
        required = math.ceil((0.75 * current_total - current_attended) / 0.25)
        return max(0, required)

    def lectures_can_skip(self):
        """Calculate how many lectures can be skipped while staying above 75%"""
        if self.total_lectures == 0:
            return 0
            
        max_total = self.attended_lectures / 0.75
        can_skip = int(max_total - self.total_lectures)
        return max(0, can_skip)

    def get_next_lectures(self, days_ahead=7):
        """Get upcoming lectures for this course"""
        today = timezone.now().date()
        end_date = today + timedelta(days=days_ahead)
        
        upcoming = []
        schedules = self.schedules.all()
        
        current_date = today
        while current_date <= end_date:
            day_name = current_date.strftime('%A').lower()
            
            for schedule in schedules:
                if schedule.day_of_week == day_name:
                    upcoming.append({
                        'date': current_date,
                        'schedule': schedule,
                        'is_today': current_date == today,
                        'days_from_now': (current_date - today).days
                    })
            
            current_date += timedelta(days=1)
        
        return sorted(upcoming, key=lambda x: x['date'])

class LectureSchedule(models.Model):
    DAYS_OF_WEEK = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=100, blank=True, help_text="Classroom or location")
    professor = models.CharField(max_length=100, blank=True, help_text="Professor name")
    
    class Meta:
        unique_together = ['course', 'day_of_week', 'start_time']
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f"{self.course.name} - {self.get_day_of_week_display()} {self.start_time}"

    @property
    def duration_minutes(self):
        """Calculate lecture duration in minutes"""
        start_datetime = datetime.combine(date.today(), self.start_time)
        end_datetime = datetime.combine(date.today(), self.end_time)
        return int((end_datetime - start_datetime).total_seconds() / 60)

    def get_next_occurrence(self):
        """Get the next date this lecture will occur"""
        today = timezone.now().date()
        days_ahead = 0
        
        # Map day names to numbers (Monday = 0, Sunday = 6)
        day_mapping = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        target_day = day_mapping[self.day_of_week]
        current_day = today.weekday()
        
        if target_day > current_day:
            days_ahead = target_day - current_day
        elif target_day < current_day:
            days_ahead = 7 - (current_day - target_day)
        else:  # Same day
            # Check if the lecture time has passed today
            now = timezone.now().time()
            if self.start_time > now:
                days_ahead = 0  # Today
            else:
                days_ahead = 7  # Next week
        
        return today + timedelta(days=days_ahead)

class AttendanceRecord(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='records')
    date = models.DateField()
    attended = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    schedule = models.ForeignKey(LectureSchedule, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ['course', 'date']
        ordering = ['-date']

    def __str__(self):
        status = "Present" if self.attended else "Absent"
        return f"{self.course.name} - {self.date} - {status}"

class Timetable(models.Model):
    """Weekly timetable view for a user"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, default="My Timetable")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s {self.name}"
    
    def get_weekly_schedule(self):
        """Get organized weekly schedule"""
        schedule = {day[0]: [] for day in LectureSchedule.DAYS_OF_WEEK}
        
        lectures = LectureSchedule.objects.filter(
            course__user=self.user
        ).select_related('course').order_by('start_time')
        
        for lecture in lectures:
            schedule[lecture.day_of_week].append(lecture)
        
        return schedule
    
    def get_today_schedule(self):
        """Get today's lectures"""
        today = timezone.now().strftime('%A').lower()
        return LectureSchedule.objects.filter(
            course__user=self.user,
            day_of_week=today
        ).select_related('course').order_by('start_time')
    
    def get_upcoming_lectures(self, days=7):
        """Get upcoming lectures with smart suggestions"""
        upcoming = []
        courses = Course.objects.filter(user=self.user)
        
        for course in courses:
            next_lectures = course.get_next_lectures(days)
            for lecture_info in next_lectures:
                suggestion = self._get_lecture_suggestion(course, lecture_info)
                upcoming.append({
                    'course': course,
                    'lecture_info': lecture_info,
                    'suggestion': suggestion
                })
        
        return sorted(upcoming, key=lambda x: (x['lecture_info']['date'], x['lecture_info']['schedule'].start_time))
    
    def _get_lecture_suggestion(self, course, lecture_info):
        """Generate smart suggestion for a specific lecture"""
        if course.is_below_threshold:
            needed = course.lectures_needed_for_75_percent()
            return {
                'type': 'critical',
                'message': f'Must attend! Need {needed} more lectures to reach 75%',
                'priority': 'high',
                'action': 'attend'
            }
        elif course.attendance_percentage < 80:
            return {
                'type': 'warning',
                'message': f'Recommended to attend (currently {course.attendance_percentage}%)',
                'priority': 'medium',
                'action': 'attend'
            }
        else:
            can_skip = course.lectures_can_skip()
            if can_skip > 0:
                return {
                    'type': 'safe',
                    'message': f'Can skip if needed (can skip {can_skip} more)',
                    'priority': 'low',
                    'action': 'optional'
                }
            else:
                return {
                    'type': 'caution',
                    'message': 'Better to attend to maintain buffer',
                    'priority': 'medium',
                    'action': 'attend'
                }
