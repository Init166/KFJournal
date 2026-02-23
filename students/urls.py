# students/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Аутентификация
    path('login/', views.student_login, name='student_login'),
    path('logout/', views.student_logout, name='student_logout'),
    
    # Основные страницы
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('schedule/', views.student_schedule, name='student_schedule'),
    path('attendance/', views.student_attendance, name='student_attendance'),
    path('priority/', views.student_priority, name='student_priority'),
    
    # API (опционально)
    path('api/grades/', views.api_get_grades, name='api_grades'),
    path('api/schedule/', views.api_get_schedule, name='api_schedule'),
]