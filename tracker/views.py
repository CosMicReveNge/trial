from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import json
from datetime import datetime, date, timedelta
from .models import Course, LectureSchedule, AttendanceRecord, Timetable, TimetableSlot
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User

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

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Check if username exists
        try:
            user_exists = User.objects.get(username=username)
            # Username exists, now check password
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, 'Username/Password is incorrect.')
        except User.DoesNotExist:
            messages.error(request, 'Username does not exist.')
    
    return render(request, 'registration/login.html')

@login_required
def dashboard(request):
    courses = Course.objects.filter(user=request.user).order_by('name')
    
    # Get or create timetable and refresh if needed
    timetable, created = Timetable.objects.get_or_create(user=request.user)
    if timetable.refresh_weekly():
        messages.info(request, 'Timetable refreshed for the new week!')
    
    # Calculate overall stats
    total_courses = courses.count()
    regular_courses = courses.filter(is_regular=True)
    courses_below_75 = sum(1 for course in regular_courses if course.attendance_percentage < 75)
    
    # Get upcoming lectures with suggestions (only for regular courses)
    upcoming_lectures = timetable.get_upcoming_lectures(days=3)[:5]  # Next 5 lectures
    
    # Get suggestions for each regular course
    suggestions = []
    for course in regular_courses:
        if course.is_below_threshold:
            needed = course.lectures_needed_for_75_percent()
            next_lectures = course.get_next_lectures(days=7)
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
        'regular_courses': regular_courses,
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
    if timetable.refresh_weekly():
        messages.info(request, 'Timetable refreshed for the new week!')
    
    weekly_schedule = timetable.get_weekly_schedule()
    upcoming_lectures = timetable.get_upcoming_lectures(days=7)
    
    # Time slots for display (6 AM to 10 PM)
    time_slots = []
    for hour in range(6, 23):  # 6 AM to 10 PM
        time_slots.append(f"{hour:02d}:00")
        time_slots.append(f"{hour:02d}:30")
    
    # Get current week dates for manual slot booking
    current_week_start = timetable.get_current_week_start()
    week_dates = []
    for i in range(7):
        week_dates.append(current_week_start + timedelta(days=i))
    
    context = {
        'timetable': timetable,
        'weekly_schedule': weekly_schedule,
        'upcoming_lectures': upcoming_lectures,
        'time_slots': time_slots,
        'days_of_week': LectureSchedule.DAYS_OF_WEEK,
        'week_dates': week_dates,
        'current_week_start': current_week_start,
        'slot_types': TimetableSlot.SLOT_TYPES,
    }
    return render(request, 'tracker/timetable.html', context)

@login_required
def add_course(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        total_lectures = int(request.POST.get('total_lectures', 0))
        attended_lectures = int(request.POST.get('attended_lectures', 0))
        is_regular = request.POST.get('is_regular') == 'on'
        
        if attended_lectures > total_lectures:
            messages.error(request, 'Attended lectures cannot exceed total lectures.')
            return redirect('dashboard')
        
        course, created = Course.objects.get_or_create(
            user=request.user,
            name=name,
            defaults={
                'total_lectures': total_lectures,
                'attended_lectures': attended_lectures,
                'is_regular': is_regular
            }
        )
        
        if created:
            messages.success(request, f'Course "{name}" added successfully!')
            
            # If it's a regular course, redirect to add schedule
            if is_regular:
                return redirect('add_course_schedule', course_id=course.id)
        else:
            messages.error(request, f'Course "{name}" already exists.')
    
    return redirect('dashboard')

@login_required
def add_course_schedule(request, course_id):
    """Add schedule for a regular course"""
    course = get_object_or_404(Course, id=course_id, user=request.user, is_regular=True)
    
    if request.method == 'POST':
        # Handle multiple schedule entries
        days = request.POST.getlist('days')
        start_times = request.POST.getlist('start_times')
        end_times = request.POST.getlist('end_times')
        rooms = request.POST.getlist('rooms')
        professors = request.POST.getlist('professors')
        
        schedules_created = 0
        for i in range(len(days)):
            if days[i] and start_times[i] and end_times[i]:
                schedule, created = LectureSchedule.objects.get_or_create(
                    course=course,
                    day_of_week=days[i],
                    start_time=start_times[i],
                    defaults={
                        'end_time': end_times[i],
                        'room': rooms[i] if i < len(rooms) else '',
                        'professor': professors[i] if i < len(professors) else ''
                    }
                )
                if created:
                    schedules_created += 1
        
        if schedules_created > 0:
            messages.success(request, f'{schedules_created} schedule(s) added for {course.name}!')
        
        return redirect('dashboard')
    
    context = {
        'course': course,
        'days_of_week': LectureSchedule.DAYS_OF_WEEK,
    }
    return render(request, 'tracker/add_course_schedule.html', context)

@login_required
def book_manual_slot(request):
    """Book a manual time slot in the timetable"""
    if request.method == 'POST':
        try:
            timetable, _ = Timetable.objects.get_or_create(user=request.user)

            title = request.POST.get('title')
            slot_type = request.POST.get('slot_type')
            date_str = request.POST.get('date')
            start_time_str = request.POST.get('start_time')
            end_time_str = request.POST.get('end_time')
            notes = request.POST.get('notes', '')

            # Parse date
            slot_date = datetime.strptime(date_str, '%Y-%m-%d').date()

            # ✅ Parse time strings into time objects
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            end_time = datetime.strptime(end_time_str, '%H:%M').time()

            # Create the slot
            slot = TimetableSlot(
                timetable=timetable,
                title=title,
                slot_type=slot_type,
                date=slot_date,
                start_time=start_time,
                end_time=end_time,
                notes=notes
            )

            # Check for conflicts
            has_conflict, conflict_message = slot.has_conflict()
            if has_conflict:
                messages.error(request, f'Time slot conflict: {conflict_message}')
                return redirect('timetable')

            # Validate and save
            slot.full_clean()
            slot.save()

            messages.success(request, f'Time slot "{title}" booked successfully!')

        except ValidationError as e:
            messages.error(request, f'Validation error: {e}')
        except Exception as e:
            messages.error(request, f'Error booking slot: {str(e)}')

    return redirect('timetable')

@login_required
def delete_manual_slot(request, slot_id):
    """Delete a manual time slot"""
    slot = get_object_or_404(TimetableSlot, id=slot_id, timetable__user=request.user)
    slot_title = slot.title
    slot.delete()
    messages.success(request, f'Time slot "{slot_title}" deleted successfully!')
    return redirect('timetable')

@login_required
def edit_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, user=request.user)
    
    if request.method == 'POST':
        course.name = request.POST.get('name')
        course.total_lectures = int(request.POST.get('total_lectures', 0))
        course.attended_lectures = int(request.POST.get('attended_lectures', 0))
        was_regular = course.is_regular
        course.is_regular = request.POST.get('is_regular') == 'on'
        
        if course.attended_lectures > course.total_lectures:
            messages.error(request, 'Attended lectures cannot exceed total lectures.')
        else:
            course.save()
            messages.success(request, 'Course updated successfully!')
            
            # If course became regular, redirect to add schedule
            if course.is_regular and not was_regular:
                return redirect('add_course_schedule', course_id=course.id)
        
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
    upcoming_lectures = course.get_next_lectures(days=14) if course.is_regular else []
    
    context = {
        'course': course,
        'schedules': schedules,
        'recent_records': recent_records,
        'upcoming_lectures': upcoming_lectures,
        'lectures_needed': course.lectures_needed_for_75_percent() if course.is_regular else 0,
        'lectures_can_skip': course.lectures_can_skip() if course.is_regular else 0,
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
    courses = Course.objects.filter(user=request.user, is_regular=True)
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
