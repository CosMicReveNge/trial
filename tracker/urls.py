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
    path('edit-course/<int:course_id>/', views.edit_course, name='edit_course'),
    path('delete-course/<int:course_id>/', views.delete_course, name='delete_course'),
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    
    # Attendance URLs
    path('update-attendance/', views.update_attendance, name='update_attendance'),
    
    # Schedule URLs
    path('course/<int:course_id>/add-schedule/', views.add_schedule, name='add_schedule'),
    
    # API URLs
    path('api/suggestions/', views.suggestions_api, name='suggestions_api'),
]
