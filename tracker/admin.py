from django.contrib import admin
from .models import Course, LectureSchedule, AttendanceRecord

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'attendance_percentage', 'attended_lectures', 'total_lectures', 'created_at']
    list_filter = ['user', 'created_at']
    search_fields = ['name', 'user__username']
    readonly_fields = ['attendance_percentage']
    
    def attendance_percentage(self, obj):
        return f"{obj.attendance_percentage}%"
    attendance_percentage.short_description = 'Attendance %'

@admin.register(LectureSchedule)
class LectureScheduleAdmin(admin.ModelAdmin):
    list_display = ['course', 'day_of_week', 'start_time', 'end_time']
    list_filter = ['day_of_week', 'course__user']
    search_fields = ['course__name']

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ['course', 'date', 'attended', 'notes']
    list_filter = ['attended', 'date', 'course__user']
    search_fields = ['course__name', 'notes']
    date_hierarchy = 'date'
