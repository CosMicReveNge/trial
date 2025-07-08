from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication URLs
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Course Management URLs
    path('add-course/', views.add_course, name='add_course'),
    path('course/<int:course_id>/add-schedule/', views.add_course_schedule, name='add_course_schedule'),
    path('edit-course/<int:course_id>/', views.edit_course, name='edit_course'),
    path('delete-course/<int:course_id>/', views.delete_course, name='delete_course'),
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    
    # Timetable URLs
    path('timetable/', views.timetable_view, name='timetable'),
    path('book-slot/', views.book_manual_slot, name='book_manual_slot'),
    path('delete-slot/<int:slot_id>/', views.delete_manual_slot, name='delete_manual_slot'),
    
    # Attendance URLs
    path('update-attendance/', views.update_attendance, name='update_attendance'),
    path('mark-attendance/', views.mark_attendance_for_date, name='mark_attendance_for_date'),
    
    # Schedule URLs
    path('course/<int:course_id>/add-schedule-detail/', views.add_schedule, name='add_schedule'),
    path('delete-schedule/<int:schedule_id>/', views.delete_schedule, name='delete_schedule'),
    
    # API URLs
    path('api/suggestions/', views.suggestions_api, name='suggestions_api'),
]
