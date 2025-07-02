from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
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
        
        # Formula: Required = ceil((0.75 * (Total + x) - Attended) / (1 - 0.75))
        # Where x is additional lectures
        current_total = self.total_lectures
        current_attended = self.attended_lectures
        
        # We need to find x such that (current_attended + x) / (current_total + x) >= 0.75
        # Solving: current_attended + x >= 0.75 * (current_total + x)
        # x >= (0.75 * current_total - current_attended) / 0.25
        
        if current_total == 0:
            return 1
            
        required = math.ceil((0.75 * current_total - current_attended) / 0.25)
        return max(0, required)

    def lectures_can_skip(self):
        """Calculate how many lectures can be skipped while staying above 75%"""
        if self.total_lectures == 0:
            return 0
            
        # Find maximum x such that current_attended / (current_total + x) >= 0.75
        # current_attended >= 0.75 * (current_total + x)
        # x <= (current_attended / 0.75) - current_total
        
        max_total = self.attended_lectures / 0.75
        can_skip = int(max_total - self.total_lectures)
        return max(0, can_skip)

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
    
    class Meta:
        unique_together = ['course', 'day_of_week', 'start_time']

    def __str__(self):
        return f"{self.course.name} - {self.get_day_of_week_display()} {self.start_time}"

class AttendanceRecord(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='records')
    date = models.DateField()
    attended = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['course', 'date']
        ordering = ['-date']

    def __str__(self):
        status = "Present" if self.attended else "Absent"
        return f"{self.course.name} - {self.date} - {status}"
