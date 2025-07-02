from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import models  # Add this import
import json
from datetime import datetime, date
from .models import Course, LectureSchedule, AttendanceRecord

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def dashboard(request):
    courses = Course.objects.filter(user=request.user).order_by('name')
    
    # Calculate overall stats
    total_courses = courses.count()
    # Fix this line - calculate courses below 75% properly
    courses_below_75 = sum(1 for course in courses if course.attendance_percentage < 75)
    
    # Get suggestions for each course
    suggestions = []
    for course in courses:
        if course.is_below_threshold:
            needed = course.lectures_needed_for_75_percent()
            suggestions.append({
                'course': course.name,
                'type': 'attend',
                'message': f'Attend next {needed} lecture(s) to reach 75%',
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
    }
    return render(request, 'tracker/dashboard.html', context)

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
        action = data.get('action')  # 'increment' or 'decrement'
        
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
    
    context = {
        'course': course,
        'schedules': schedules,
        'recent_records': recent_records,
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
        
        schedule, created = LectureSchedule.objects.get_or_create(
            course=course,
            day_of_week=day_of_week,
            start_time=start_time,
            defaults={'end_time': end_time}
        )
        
        if created:
            messages.success(request, 'Schedule added successfully!')
        else:
            messages.error(request, 'Schedule already exists for this time slot.')
    
    return redirect('course_detail', course_id=course_id)

@login_required
def suggestions_api(request):
    courses = Course.objects.filter(user=request.user)
    suggestions = []
    
    for course in courses:
        if course.is_below_threshold:
            needed = course.lectures_needed_for_75_percent()
            suggestions.append({
                'course_id': course.id,
                'course_name': course.name,
                'type': 'critical',
                'message': f'Must attend next {needed} lecture(s) to reach 75%',
                'current_percentage': course.attendance_percentage,
                'lectures_needed': needed
            })
        elif course.attendance_percentage < 80:  # Warning zone
            suggestions.append({
                'course_id': course.id,
                'course_name': course.name,
                'type': 'warning',
                'message': f'Close to threshold - current: {course.attendance_percentage}%',
                'current_percentage': course.attendance_percentage,
                'lectures_needed': 0
            })
        else:
            can_skip = course.lectures_can_skip()
            if can_skip > 0:
                suggestions.append({
                    'course_id': course.id,
                    'course_name': course.name,
                    'type': 'safe',
                    'message': f'Can skip {can_skip} lecture(s) safely',
                    'current_percentage': course.attendance_percentage,
                    'can_skip': can_skip
                })
    
    return JsonResponse({'suggestions': suggestions})
