from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.elder_login, name='elder_login'),
    path('logout/', views.elder_logout, name='elder_logout'),
    path('dashboard/', views.elder_dashboard, name='elder_dashboard'),
    path('schedule/', views.elder_schedule, name='elder_schedule'),
    path('attendance/', views.elder_attendance, name='elder_attendance'),
    path('grades/', views.elder_grades, name='elder_grades'),
    path('students/', views.elder_students, name='elder_students'),
    path('student/<int:student_id>/', views.student_detail, name='student_detail'),
    
    # API
    path('api/get-schedule/', views.api_get_schedule, name='api_get_schedule'),
    path('api/add-lesson/', views.api_add_lesson, name='api_add_lesson'),
    path('api/update-lesson/', views.api_update_lesson, name='api_update_lesson'),
    path('api/delete-lesson/', views.api_delete_lesson, name='api_delete_lesson'),
    path('api/get-lesson/<int:lesson_id>/', views.api_get_lesson, name='api_get_lesson'),
    
    # Оценки
    path('api/add-grade/', views.api_add_grade, name='api_add_grade'),
    path('api/delete-grade/', views.api_delete_grade, name='api_delete_grade'),
    path('api/get-subjects/', views.api_get_subjects, name='api_get_subjects'),
    path('api/students-with-points/', views.api_students_with_points, name='api_students_with_points'),
    path('api/student-points/', views.api_student_points, name='api_student_points'),
    
    # Пропуски
    path('api/add-attendance/', views.api_add_attendance, name='api_add_attendance'),
    path('api/delete-attendance/', views.api_delete_attendance, name='api_delete_attendance'),
    path('api/attendance-history/', views.api_attendance_history, name='api_attendance_history'),
    
    # Студенты
    path('api/add-student/', views.api_add_student, name='api_add_student'),
    path('api/update-student/', views.api_update_student, name='api_update_student'),
    path('api/delete-student/', views.api_delete_student, name='api_delete_student'),
    path('api/get-student/<int:student_id>/', views.api_get_student, name='api_get_student'),
    path('api/update-student-password/', views.api_update_student_password, name='api_update_student_password'),
    path('api/generate-password/', views.api_generate_password, name='api_generate_password'),
    
    # Комментарии
    path('api/add-comment/', views.api_add_comment, name='api_add_comment'),
    path('api/get-comments/', views.api_get_comments, name='api_get_comments'),
    path('api/delete-comment/', views.api_delete_comment, name='api_delete_comment'),
    
    # Семинары
    path('api/seminar-slots/', views.api_seminar_slots, name='api_seminar_slots'),
    path('api/assign-slot/', views.api_assign_slot, name='api_assign_slot'),
    path('api/remove-slot/', views.api_remove_slot, name='api_remove_slot'),
    path('api/get-subject-id/', views.api_get_subject_id, name='api_get_subject_id'),
]