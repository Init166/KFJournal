# core/views.py
from django.shortcuts import render
from django.http import Http404

def home(request):
    """Главная страница с выбором роли"""
    return render(request, 'core/index.html')

def page_404(request):
    """Тестовая страница 404 ошибки (доступна по прямой ссылке)"""
    return render(request, 'errors/404.html', {'is_test': True})

def custom_404_view(request, exception=None):
    """Обработчик реальных 404 ошибок"""
    return render(request, 'errors/404.html', status=404)