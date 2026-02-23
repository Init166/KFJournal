from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),
    
    # Навигация и контент
    path('api/folder-content/', views.get_folder_content, name='folder_content'),
    path('api/student/<int:student_id>/', views.get_student, name='get_student'),
    
    # CRUD операции
    path('api/create/', views.create_item, name='create_item'),
    path('api/update/', views.update_item, name='update_item'),
    path('api/delete/', views.delete_item, name='delete_item'),
    path('api/rename/', views.rename_item, name='rename_item'),
    path('api/move-item/', views.move_item, name='move_item'),
    
    # Поиск и логи
    path('api/search/', views.search_items, name='search_items'),
    path('api/navigation-history/', views.get_navigation_history, name='navigation_history'),
    path('api/action-logs/', views.get_action_logs, name='action_logs'),
    
    # Кэш
    path('api/clear-cache/', views.clear_cache, name='clear_cache'),

    # Корзина
    path('api/restore/', views.restore_item, name='restore_item'),
    path('api/trash/', views.get_trash, name='get_trash'),

    # Управление паролями
    path('api/passwords/', views.view_passwords, name='view_passwords'),
    path('api/generate-password/', views.generate_and_set_password, name='generate_password'),
]