from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import models  # Add this import
from django.utils import timezone
import json
from datetime import datetime, date, timedelta
from .models import Course, LectureSchedule, AttendanceRecord, Timetable

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            login(request, user)
            # Create timetable for new user
            Timetable.objects.get_or_create(user=user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def dashboard(request):
    courses = Course.objects.filter(user=request.user).order_by('name')
    
    # Get or create timetable
    timetable, created = Timetable.objects.get_or_create(user=request.user)
    
    # Calculate overall stats
    total_courses = courses.count()
    courses_below_75 = sum(1 for course in courses if course.attendance_percentage < 75)
    
    # Get upcoming lectures with suggestions
    upcoming_lectures = timetable.get_upcoming_lectures(days=3)[:5]  # Next 5 lectures
    
    # Get suggestions for each course
    suggestions = []
    for course in courses:
        if course.is_below_threshold:
            needed = course.lectures_needed_for_75_percent()
            next_lectures = course.get_next_lectures(days_ahead=7)
            next_lecture_text = ""
            if next_lectures:
                next_lecture = next_lectures[0]
                next_lecture_text = f" (Next: {next_lecture['schedule'].get_day_of_week_display()} {next_lecture['schedule'].start_time})"
            
            suggestions.append({
                'course': course.name,
                'type': 'attend',
                'message': f'Attend next {needed} lecture(s) to reach 75%{next_lecture_text}',
                'priority': 'high'
            })
        else:
            can_skip = course.lectures_can_skip()
            if can_skip > 0:
                suggestions.append({
                    'course': course.name,
                    'type': 'skip',
                    'message': f'You can skip {can_skip} lecture(s) and stay above 75%',
                    'priority': 'low'
                })
    
    context = {
        'courses': courses,
        'total_courses': total_courses,
        'courses_below_75': courses_below_75,
        'suggestions': suggestions,
        'upcoming_lectures': upcoming_lectures,
        'today_schedule': timetable.get_today_schedule(),
    }
    return render(request, 'tracker/dashboard.html', context)

@login_required
def timetable_view(request):
    """Display weekly timetable"""
    timetable, created = Timetable.objects.get_or_create(user=request.user)
    weekly_schedule = timetable.get_weekly_schedule()
    upcoming_lectures = timetable.get_upcoming_lectures(days=7)
    
    # Time slots for display (8 AM to 8 PM)
    time_slots = []
    for hour in range(8, 21):  # 8 AM to 8 PM
        time_slots.append(f"{hour:02d}:00")
        time_slots.append(f"{hour:02d}:30")
    
    context = {
        'timetable': timetable,
        'weekly_schedule': weekly_schedule,
        'upcoming_lectures': upcoming_lectures,
        'time_slots': time_slots,
        'days_of_week': LectureSchedule.DAYS_OF_WEEK,
    }
    return render(request, 'tracker/timetable.html', context)

@login_required
def add_course(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        total_lectures = int(request.POST.get('total_lectures', 0))
        attended_lectures = int(request.POST.get('attended_lectures', 0))
        
        if attended_lectures > total_lectures:
            messages.error(request, 'Attended lectures cannot exceed total lectures.')
            return redirect('dashboard')
        
        course, created = Course.objects.get_or_create(
            user=request.user,
            name=name,
            defaults={
                'total_lectures': total_lectures,
                'attended_lectures': attended_lectures
            }
        )
        
        if created:
            messages.success(request, f'Course "{name}" added successfully!')
        else:
            messages.error(request, f'Course "{name}" already exists.')
    
    return redirect('dashboard')

@login_required
def edit_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, user=request.user)
    
    if request.method == 'POST':
        course.name = request.POST.get('name')
        course.total_lectures = int(request.POST.get('total_lectures', 0))
        course.attended_lectures = int(request.POST.get('attended_lectures', 0))
        
        if course.attended_lectures > course.total_lectures:
            messages.error(request, 'Attended lectures cannot exceed total lectures.')
        else:
            course.save()
            messages.success(request, 'Course updated successfully!')
        
        return redirect('dashboard')
    
    return render(request, 'tracker/edit_course.html', {'course': course})

@login_required
def delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, user=request.user)
    course_name = course.name
    course.delete()
    messages.success(request, f'Course "{course_name}" deleted successfully!')
    return redirect('dashboard')

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_attendance(request):
    try:
        data = json.loads(request.body)
        course_id = data.get('course_id')
        action = data.get('action')
        
        course = get_object_or_404(Course, id=course_id, user=request.user)
        
        if action == 'increment':
            course.attended_lectures += 1
            course.total_lectures += 1
        elif action == 'decrement' and course.attended_lectures > 0:
            course.attended_lectures -= 1
        elif action == 'add_total':
            course.total_lectures += 1
        elif action == 'remove_total' and course.total_lectures > 0:
            course.total_lectures -= 1
            if course.attended_lectures > course.total_lectures:
                course.attended_lectures = course.total_lectures
        
        course.save()
        
        return JsonResponse({
            'success': True,
            'attendance_percentage': course.attendance_percentage,
            'attended_lectures': course.attended_lectures,
            'total_lectures': course.total_lectures,
            'is_below_threshold': course.is_below_threshold
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id, user=request.user)
    schedules = LectureSchedule.objects.filter(course=course)
    recent_records = AttendanceRecord.objects.filter(course=course)[:10]
    upcoming_lectures = course.get_next_lectures(days=14)
    
    context = {
        'course': course,
        'schedules': schedules,
        'recent_records': recent_records,
        'upcoming_lectures': upcoming_lectures,
        'lectures_needed': course.lectures_needed_for_75_percent(),
        'lectures_can_skip': course.lectures_can_skip(),
    }
    return render(request, 'tracker/course_detail.html', context)

@login_required
def add_schedule(request, course_id):
    course = get_object_or_404(Course, id=course_id, user=request.user)
    
    if request.method == 'POST':
        day_of_week = request.POST.get('day_of_week')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        room = request.POST.get('room', '')
        professor = request.POST.get('professor', '')
        
        schedule, created = LectureSchedule.objects.get_or_create(
            course=course,
            day_of_week=day_of_week,
            start_time=start_time,
            defaults={
                'end_time': end_time,
                'room': room,
                'professor': professor
            }
        )
        
        if created:
            messages.success(request, 'Schedule added successfully!')
        else:
            messages.error(request, 'Schedule already exists for this time slot.')
    
    return redirect('course_detail', course_id=course_id)

@login_required
def delete_schedule(request, schedule_id):
    schedule = get_object_or_404(LectureSchedule, id=schedule_id, course__user=request.user)
    course_id = schedule.course.id
    schedule.delete()
    messages.success(request, 'Schedule deleted successfully!')
    return redirect('course_detail', course_id=course_id)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def mark_attendance_for_date(request):
    """Mark attendance for a specific date and lecture"""
    try:
        data = json.loads(request.body)
        course_id = data.get('course_id')
        date_str = data.get('date')
        attended = data.get('attended', True)
        
        course = get_object_or_404(Course, id=course_id, user=request.user)
        attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Create or update attendance record
        record, created = AttendanceRecord.objects.get_or_create(
            course=course,
            date=attendance_date,
            defaults={'attended': attended}
        )
        
        if not created:
            # Update existing record
            old_attended = record.attended
            record.attended = attended
            record.save()
            
            # Update course totals
            if old_attended != attended:
                if attended and not old_attended:
                    course.attended_lectures += 1
                elif not attended and old_attended:
                    course.attended_lectures -= 1
        else:
            # New record
            if attended:
                course.attended_lectures += 1
            course.total_lectures += 1
        
        course.save()
        
        return JsonResponse({
            'success': True,
            'attendance_percentage': course.attendance_percentage,
            'attended_lectures': course.attended_lectures,
            'total_lectures': course.total_lectures,
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def suggestions_api(request):
    courses = Course.objects.filter(user=request.user)
    timetable, _ = Timetable.objects.get_or_create(user=request.user)
    
    suggestions = []
    upcoming_lectures = timetable.get_upcoming_lectures(days=7)
    
    # Add time-aware suggestions
    for lecture_data in upcoming_lectures:
        course = lecture_data['course']
        lecture_info = lecture_data['lecture_info']
        suggestion = lecture_data['suggestion']
        
        suggestions.append({
            'course_id': course.id,
            'course_name': course.name,
            'type': suggestion['type'],
            'message': suggestion['message'],
            'current_percentage': course.attendance_percentage,
            'lecture_date': lecture_info['date'].strftime('%Y-%m-%d'),
            'lecture_time': lecture_info['schedule'].start_time.strftime('%H:%M'),
            'lecture_day': lecture_info['schedule'].get_day_of_week_display(),
            'is_today': lecture_info['is_today'],
            'days_from_now': lecture_info['days_from_now']
        })
    
    return JsonResponse({'suggestions': suggestions})
