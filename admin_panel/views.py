import random
import string
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from django.db import models
import json
from .models import (
    EducationalLevel, StudyForm, Course, Group, 
    Student, Department, Employee, DatabaseLog,
    NavigationHistory, ActionCache, ElderPermission, DeletedItemCache
)

# ==================== КАСТОМНЫЕ ДЕКОРАТОРЫ ====================

def login_required_custom(view_func):
    """Кастомный декоратор проверки авторизации"""
    def wrapper(request, *args, **kwargs):
        if not request.session.get('admin_id') or not request.session.get('is_custom_admin'):
            print("Декоратор: нет ID в сессии, перенаправляем")
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def generate_password(length=8):
    """Генерация случайного пароля"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def get_admin_from_session(request):
    """Получение админа из сессии для логов"""
    admin_id = request.session.get('admin_id')
    if admin_id:
        try:
            return Student.objects.get(id=admin_id)
        except Student.DoesNotExist:
            pass
    return None

# ==================== АВТОРИЗАЦИЯ ====================

@csrf_exempt
def admin_login(request):
    """Страница входа в админ-панель"""
    error = None
    
    if request.method == 'POST':
        login_input = request.POST.get('username')
        password_input = request.POST.get('password')
        
        try:
            student = Student.objects.get(login=login_input)
            
            if student.password == password_input:
                if student.user_type in ['admin', 'dean'] or getattr(student, 'is_superuser', False):
                    request.session.flush()
                    request.session['admin_id'] = student.id
                    request.session['admin_name'] = student.full_name
                    request.session['admin_type'] = student.user_type
                    request.session['is_custom_admin'] = True
                    
                    return redirect('admin_dashboard')
                else:
                    error = 'Недостаточно прав для доступа к админ-панели'
            else:
                error = 'Неверный пароль'
        except Student.DoesNotExist:
            user = authenticate(request, username=login_input, password=password_input)
            
            if user and user.is_superuser:
                student, created = Student.objects.get_or_create(
                    login=user.username,
                    defaults={
                        'full_name': user.get_full_name() or user.username,
                        'password': password_input,
                        'user_type': 'admin',
                        'is_active': True,
                        'is_superuser': True
                    }
                )
                
                if not created:
                    student.user_type = 'admin'
                    student.is_superuser = True
                    student.save()
                
                request.session.flush()
                request.session['admin_id'] = student.id
                request.session['admin_name'] = student.full_name
                request.session['admin_type'] = 'admin'
                request.session['is_custom_admin'] = True
                
                return redirect('admin_dashboard')
            else:
                error = 'Неверный логин или пароль'
    
    return render(request, 'admin_panel/login.html', {'error': error})

def admin_logout(request):
    """Выход из админ-панели"""
    keys_to_remove = ['admin_id', 'admin_name', 'admin_type', 'is_custom_admin']
    for key in keys_to_remove:
        if key in request.session:
            del request.session[key]
    return redirect('admin_login')

# ==================== ОСНОВНАЯ ПАНЕЛЬ ====================

@login_required_custom
def admin_dashboard(request):
    """Главная страница админ-панели"""
    educational_levels = EducationalLevel.objects.prefetch_related(
        'forms__courses__groups__students'
    ).all()
    
    departments = Department.objects.prefetch_related('employees').all()
    recent_logs = DatabaseLog.objects.all()[:10]
    
    context = {
        'educational_levels': educational_levels,
        'departments': departments,
        'departments_count': departments.count(),
        'recent_logs': recent_logs,
    }
    
    return render(request, 'admin_panel/dashboard.html', context)

# ==================== ПОЛУЧЕНИЕ ДАННЫХ ====================

@login_required_custom
def get_folder_content(request):
    """Получение содержимого папки"""
    folder_type = request.GET.get('type')
    folder_id = request.GET.get('id')
    
    data = {
        'type': folder_type,
        'id': folder_id,
        'items': [],
        'path': []
    }
    
    try:
        if folder_type == 'level':
            level = get_object_or_404(EducationalLevel, id=folder_id)
            data['title'] = level.name
            data['path'] = [{'type': 'level', 'id': level.id, 'name': level.name}]
            
            for form in level.forms.all():
                data['items'].append({
                    'type': 'form',
                    'id': form.id,
                    'name': form.name,
                    'icon': 'bi-folder',
                    'count': form.student_count()
                })
                
        elif folder_type == 'form':
            form = get_object_or_404(StudyForm, id=folder_id)
            data['title'] = form.name
            data['path'] = [
                {'type': 'level', 'id': form.level.id, 'name': form.level.name},
                {'type': 'form', 'id': form.id, 'name': form.name}
            ]
            
            for course in form.courses.all():
                data['items'].append({
                    'type': 'course',
                    'id': course.id,
                    'name': f'{course.number} курс',
                    'icon': 'bi-layers',
                    'count': course.student_count()
                })
                
        elif folder_type == 'course':
            course = get_object_or_404(Course, id=folder_id)
            data['title'] = f'{course.number} курс'
            data['path'] = [
                {'type': 'level', 'id': course.form.level.id, 'name': course.form.level.name},
                {'type': 'form', 'id': course.form.id, 'name': course.form.name},
                {'type': 'course', 'id': course.id, 'name': f'{course.number} курс'}
            ]
            
            for group in course.groups.all():
                data['items'].append({
                    'type': 'group',
                    'id': group.id,
                    'name': group.name,
                    'icon': 'bi-people',
                    'count': group.students.count(),
                })
                
        elif folder_type == 'group':
            group = get_object_or_404(Group, id=folder_id)
            data['title'] = group.name
            data['path'] = [
                {'type': 'level', 'id': group.level.id, 'name': group.level.name},
                {'type': 'form', 'id': group.form.id, 'name': group.form.name},
                {'type': 'course', 'id': group.course.id, 'name': f'{group.course.number} курс'},
                {'type': 'group', 'id': group.id, 'name': group.name}
            ]
            
            students = group.students.all().order_by('full_name')
            for student in students:
                data['items'].append({
                    'type': 'student',
                    'id': student.id,
                    'full_name': student.full_name,
                    'name': student.full_name,
                    'icon': 'bi-person-circle',
                    'login': student.login,
                    'email': student.email or '',
                    'phone': student.phone or '',
                    'user_type': student.user_type,
                    'is_elder': student.is_elder,
                    'is_active': student.is_active
                })
        
        # Сохраняем в историю навигации
        admin = get_admin_from_session(request)
        if admin:
            try:
                NavigationHistory.objects.create(
                    user_id=admin.id,
                    content_type=folder_type,
                    object_id=int(folder_id),
                    title=data.get('title', 'Без названия'),
                    path=' → '.join([p['name'] for p in data.get('path', [])])
                )
            except Exception as e:
                print(f"Ошибка сохранения истории: {e}")
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse(data)

@login_required_custom
def get_student(request, student_id):
    """Получение данных студента для редактирования"""
    try:
        student = Student.objects.get(id=student_id)
        
        permissions = {}
        try:
            if hasattr(student, 'permissions'):
                perm_obj = student.permissions
                permissions = {
                    'add_students': perm_obj.permissions.get('add_students', False),
                    'edit_students': perm_obj.permissions.get('edit_students', False),
                    'delete_students': perm_obj.permissions.get('delete_students', False),
                    'manage_schedule': perm_obj.permissions.get('manage_schedule', False),
                    'manage_attendance': perm_obj.permissions.get('manage_attendance', False),
                    'manage_grades': perm_obj.permissions.get('manage_grades', False),
                    'create_chat': perm_obj.permissions.get('create_chat', False),
                    'export_reports': perm_obj.permissions.get('export_reports', False),
                    'max_students': perm_obj.max_students,
                    'can_manage_elders': perm_obj.can_manage_elders,
                }
        except:
            permissions = {}
        
        data = {
            'id': student.id,
            'full_name': student.full_name,
            'login': student.login,
            'password': student.password,
            'email': student.email or '',
            'phone': student.phone or '',
            'user_type': student.user_type,
            'is_elder': student.is_elder,
            'is_active': student.is_active,
            'group_id': student.group.id if student.group else None,
            'group_name': student.group.name if student.group else 'Нет группы',
            'permissions': permissions,
            'created_at': student.created_at.strftime('%d.%m.%Y') if student.created_at else '',
        }
        return JsonResponse(data)
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Студент не найден'}, status=404)

# ==================== СОЗДАНИЕ ЭЛЕМЕНТОВ ====================

@login_required_custom
@csrf_exempt
def create_item(request):
    """API для создания нового элемента"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            item_type = data.get('type')
            admin = get_admin_from_session(request)
            
            if item_type == 'student':
                is_elder = data.get('is_elder') == 'on' or data.get('is_elder') == True
                user_type = data.get('user_type', 'student')
                
                if Student.objects.filter(login=data.get('login')).exists():
                    return JsonResponse({
                        'success': False, 
                        'error': f'Студент с логином "{data.get("login")}" уже существует'
                    }, status=400)
                
                student = Student.objects.create(
                    login=data.get('login'),
                    full_name=data.get('full_name'),
                    email=data.get('email', ''),
                    phone=data.get('phone', ''),
                    group_id=data.get('group_id'),
                    user_type=user_type,
                    is_elder=is_elder if user_type == 'student' else False,
                    is_active=True
                )
                
                if user_type == 'elder' or is_elder:
                    ElderPermission.objects.get_or_create(student=student)
                
                DatabaseLog.objects.create(
                    user_id=admin.id if admin else None,
                    user_type=admin.user_type if admin else None,
                    user_name=admin.full_name if admin else 'Система',
                    action='create',
                    model_name='Student',
                    object_id=student.id,
                    details={'student': student.full_name, 'login': student.login},
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                return JsonResponse({'success': True, 'id': student.id})
                
            elif item_type == 'level':
                if EducationalLevel.objects.filter(name=data.get('name')).exists():
                    return JsonResponse({
                        'success': False, 
                        'error': f'Уровень образования "{data.get("name")}" уже существует'
                    }, status=400)
                
                level = EducationalLevel.objects.create(
                    name=data.get('name'),
                    order=data.get('order', 0)
                )
                
                DatabaseLog.objects.create(
                    user_id=admin.id if admin else None,
                    user_type=admin.user_type if admin else None,
                    user_name=admin.full_name if admin else 'Система',
                    action='create',
                    model_name='EducationalLevel',
                    object_id=level.id,
                    details={'level': level.name},
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                return JsonResponse({'success': True, 'id': level.id})
                
            elif item_type == 'form':
                if StudyForm.objects.filter(
                    name=data.get('name'), 
                    level_id=data.get('level_id')
                ).exists():
                    return JsonResponse({
                        'success': False, 
                        'error': f'Форма обучения "{data.get("name")}" уже существует в этом уровне'
                    }, status=400)
                
                form = StudyForm.objects.create(
                    name=data.get('name'),
                    level_id=data.get('level_id'),
                    order=data.get('order', 0)
                )
                
                return JsonResponse({'success': True, 'id': form.id})
                
            elif item_type == 'course':
                if Course.objects.filter(
                    number=data.get('number'),
                    form_id=data.get('form_id')
                ).exists():
                    return JsonResponse({
                        'success': False, 
                        'error': f'Курс {data.get("number")} уже существует в этой форме обучения'
                    }, status=400)
                
                course = Course.objects.create(
                    number=data.get('number'),
                    form_id=data.get('form_id'),
                    order=data.get('order', 0)
                )
                
                return JsonResponse({'success': True, 'id': course.id})
                
            elif item_type == 'group':
                course_id = data.get('course_id')
                if not course_id:
                    return JsonResponse({'success': False, 'error': 'Не указан курс'}, status=400)
                
                if Group.objects.filter(
                    name=data.get('name'),
                    course_id=course_id
                ).exists():
                    return JsonResponse({
                        'success': False, 
                        'error': f'Группа "{data.get("name")}" уже существует на этом курсе'
                    }, status=400)
                
                course = get_object_or_404(Course, id=course_id)
                
                group = Group.objects.create(
                    name=data.get('name'),
                    course=course,
                    form=course.form,
                    level=course.form.level
                )
                
                DatabaseLog.objects.create(
                    user_id=admin.id if admin else None,
                    user_type=admin.user_type if admin else None,
                    user_name=admin.full_name if admin else 'Система',
                    action='create',
                    model_name='Group',
                    object_id=group.id,
                    details={'group': group.name, 'course': course.number},
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                return JsonResponse({'success': True, 'id': group.id})
                
            else:
                return JsonResponse({'success': False, 'error': f'Неизвестный тип: {item_type}'}, status=400)
                
        except Exception as e:
            print(f"Ошибка в create_item: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

# ==================== ОБНОВЛЕНИЕ ЭЛЕМЕНТОВ ====================

@login_required_custom
@csrf_exempt
def update_item(request):
    """API для обновления элемента"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print(f"UPDATE REQUEST DATA: {data}")
            
            item_type = data.get('type')
            item_id = data.get('id')
            admin = get_admin_from_session(request)
            
            if not item_type or not item_id:
                return JsonResponse({'success': False, 'error': 'Missing type or id'}, status=400)
            
            if item_type == 'student':
                try:
                    student = Student.objects.get(id=int(item_id))
                except (ValueError, Student.DoesNotExist):
                    return JsonResponse({'success': False, 'error': 'Студент не найден'}, status=404)
                
                # Обновляем основные поля
                if 'full_name' in data and data['full_name']:
                    student.full_name = data['full_name']
                if 'login' in data and data['login']:
                    if data['login'] != student.login and Student.objects.filter(login=data['login']).exists():
                        return JsonResponse({'success': False, 'error': f'Логин "{data["login"]}" уже существует'}, status=400)
                    student.login = data['login']
                if 'password' in data and data['password']:
                    student.password = data['password']
                if 'email' in data:
                    student.email = data['email']
                if 'phone' in data:
                    student.phone = data['phone']
                if 'user_type' in data and data['user_type']:
                    student.user_type = data['user_type']
                if 'is_elder' in data:
                    student.is_elder = str(data['is_elder']).lower() in ['true', 'on', '1']
                if 'is_active' in data:
                    student.is_active = str(data['is_active']).lower() in ['true', 'on', '1']
                
                student.save()
                print(f"Student updated: {student.id} - {student.full_name}")
                
                # Обновляем права старосты
                if student.user_type == 'elder':
                    perm, created = ElderPermission.objects.get_or_create(student=student)
                    if not created:
                        perm.permissions = {
                            'add_students': str(data.get('perm_add_students', '')).lower() in ['true', 'on', '1'],
                            'edit_students': str(data.get('perm_edit_students', '')).lower() in ['true', 'on', '1'],
                            'delete_students': str(data.get('perm_delete_students', '')).lower() in ['true', 'on', '1'],
                            'manage_schedule': str(data.get('perm_manage_schedule', '')).lower() in ['true', 'on', '1'],
                            'manage_attendance': str(data.get('perm_manage_attendance', '')).lower() in ['true', 'on', '1'],
                            'manage_grades': str(data.get('perm_manage_grades', '')).lower() in ['true', 'on', '1'],
                            'create_chat': str(data.get('perm_create_chat', '')).lower() in ['true', 'on', '1'],
                            'export_reports': str(data.get('perm_export_reports', '')).lower() in ['true', 'on', '1'],
                        }
                        perm.max_students = data.get('max_students', 100)
                        perm.can_manage_elders = str(data.get('can_manage_elders', '')).lower() in ['true', 'on', '1']
                        perm.save()
                
                DatabaseLog.objects.create(
                    user_id=admin.id if admin else None,
                    user_type=admin.user_type if admin else None,
                    user_name=admin.full_name if admin else 'Система',
                    action='update',
                    model_name='Student',
                    object_id=student.id,
                    details={'student': student.full_name},
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                return JsonResponse({'success': True})
                
            else:
                return JsonResponse({'success': False, 'error': f'Неизвестный тип: {item_type}'}, status=400)
                
        except Exception as e:
            print(f"ERROR in update_item: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

# ==================== УДАЛЕНИЕ ЭЛЕМЕНТОВ ====================

@login_required_custom
@csrf_exempt
def delete_item(request):
    """API для удаления элемента"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            item_type = data.get('type')
            item_id = data.get('id')
            
            admin = get_admin_from_session(request)
            
            if item_type == 'student':
                student = get_object_or_404(Student, id=item_id)
                student_name = student.full_name
                student.delete()
                
                DatabaseLog.objects.create(
                    user_id=admin.id if admin else None,
                    user_type=admin.user_type if admin else None,
                    user_name=admin.full_name if admin else 'Система',
                    action='delete',
                    model_name='Student',
                    object_id=item_id,
                    details={'student': student_name},
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
            elif item_type == 'group':
                group = get_object_or_404(Group, id=item_id)
                group_name = group.name
                group.delete()
                DatabaseLog.objects.create(
                    user_id=admin.id if admin else None,
                    user_type=admin.user_type if admin else None,
                    user_name=admin.full_name if admin else 'Система',
                    action='delete',
                    model_name='Group',
                    object_id=item_id,
                    details={'group': group_name},
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
            elif item_type == 'course':
                course = get_object_or_404(Course, id=item_id)
                course.delete()
                
            elif item_type == 'form':
                form = get_object_or_404(StudyForm, id=item_id)
                form.delete()
                
            elif item_type == 'level':
                level = get_object_or_404(EducationalLevel, id=item_id)
                level.delete()
                
            else:
                return JsonResponse({'success': False, 'error': f'Неизвестный тип: {item_type}'}, status=400)
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

# ==================== ПОИСК ====================

@login_required_custom
def search_items(request):
    """Поиск студентов по всей базе"""
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'results': [], 'count': 0})
    
    students = Student.objects.filter(
        models.Q(full_name__icontains=query) |
        models.Q(login__icontains=query) |
        models.Q(email__icontains=query)
    ).select_related('group__course__form__level')[:50]
    
    results = []
    for student in students:
        path_parts = []
        if student.group:
            if student.group.level:
                path_parts.append(student.group.level.name)
            if student.group.form:
                path_parts.append(student.group.form.name)
            if student.group.course:
                path_parts.append(f"{student.group.course.number} курс")
            path_parts.append(student.group.name)
        
        results.append({
            'id': student.id,
            'full_name': student.full_name,
            'login': student.login,
            'email': student.email or '',
            'phone': student.phone or '',
            'user_type': student.user_type,
            'is_elder': student.is_elder,
            'is_active': student.is_active,
            'group': student.group.name if student.group else 'Нет группы',
            'path': ' → '.join(path_parts) if path_parts else 'Нет группы'
        })
    
    return JsonResponse({'results': results, 'count': len(results)})

# ==================== ПЕРЕИМЕНОВАНИЕ ====================

@login_required_custom
@csrf_exempt
def rename_item(request):
    """Переименование папки или группы"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            item_type = data.get('type')
            item_id = data.get('id')
            new_name = data.get('name')
            admin = get_admin_from_session(request)
            
            if item_type == 'level':
                item = get_object_or_404(EducationalLevel, id=item_id)
                old_name = item.name
                item.name = new_name
                item.save()
                
            elif item_type == 'form':
                item = get_object_or_404(StudyForm, id=item_id)
                old_name = item.name
                item.name = new_name
                item.save()
                
            elif item_type == 'course':
                item = get_object_or_404(Course, id=item_id)
                old_name = f'{item.number} курс'
                try:
                    item.number = int(new_name.split()[0]) if 'курс' in new_name else int(new_name)
                except ValueError:
                    return JsonResponse({'success': False, 'error': 'Неверный формат номера курса'}, status=400)
                item.save()
                
            elif item_type == 'group':
                item = get_object_or_404(Group, id=item_id)
                old_name = item.name
                item.name = new_name
                item.save()
                
            else:
                return JsonResponse({'success': False, 'error': 'Неподдерживаемый тип'}, status=400)
            
            DatabaseLog.objects.create(
                user_id=admin.id if admin else None,
                user_type=admin.user_type if admin else None,
                user_name=admin.full_name if admin else 'Система',
                action='update',
                model_name=item_type.capitalize(),
                object_id=item.id,
                details={'old_name': old_name, 'new_name': new_name},
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

# ==================== ПЕРЕМЕЩЕНИЕ ====================

@login_required_custom
@csrf_exempt
def move_item(request):
    """API для перемещения элементов между структурами"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            item_type = data.get('type')
            item_id = data.get('item_id')
            target_type = data.get('target_type')
            target_id = data.get('target_id')
            admin = get_admin_from_session(request)
            
            if item_type == 'student' and target_type == 'group':
                student = get_object_or_404(Student, id=item_id)
                old_group = student.group
                target_group = get_object_or_404(Group, id=target_id)
                
                student.group = target_group
                student.save()
                
                DatabaseLog.objects.create(
                    user_id=admin.id if admin else None,
                    user_type=admin.user_type if admin else None,
                    user_name=admin.full_name if admin else 'Система',
                    action='move',
                    model_name='Student',
                    object_id=student.id,
                    details={
                        'from': old_group.name if old_group else 'None',
                        'to': target_group.name,
                        'student': student.full_name
                    },
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                return JsonResponse({'success': True})
                
            else:
                return JsonResponse({'success': False, 'error': 'Неподдерживаемый тип перемещения'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

# ==================== ИСТОРИЯ НАВИГАЦИИ ====================

@login_required_custom
def get_navigation_history(request):
    """Получение истории навигации для кнопок Назад/Вперёд"""
    try:
        admin = get_admin_from_session(request)
        if not admin:
            return JsonResponse({'history': []})
            
        history = NavigationHistory.objects.filter(user_id=admin.id)[:50]
        
        data = [{
            'id': h.id,
            'type': h.content_type,
            'object_id': h.object_id,
            'title': h.title,
            'path': h.path,
            'time': h.created_at.strftime('%H:%M:%S')
        } for h in history]
        
        return JsonResponse({'history': data})
    except Exception as e:
        return JsonResponse({'error': str(e), 'history': []}, status=500)

# ==================== ПАРОЛИ ====================

@login_required_custom
def view_passwords(request):
    """Просмотр паролей всех пользователей (только для админов)"""
    admin_id = request.session.get('admin_id')
    if not admin_id:
        return JsonResponse({'error': 'Не авторизован'}, status=401)
    
    admin_type = request.session.get('admin_type')
    if admin_type != 'admin':
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    try:
        students = Student.objects.select_related('group').all()
        
        data = [{
            'id': s.id,
            'login': s.login,
            'password': s.password,
            'full_name': s.full_name,
            'user_type': s.get_user_type_display(),
            'group': s.group.name if s.group else '—',
            'is_active': s.is_active
        } for s in students]
        
        return JsonResponse({'passwords': data})
    except Exception as e:
        print(f"Ошибка в view_passwords: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required_custom
@csrf_exempt
@require_http_methods(["POST"])
def generate_and_set_password(request):
    """Генерация и установка пароля для пользователя"""
    admin_id = request.session.get('admin_id')
    if not admin_id:
        return JsonResponse({'error': 'Не авторизован'}, status=401)
    
    admin_type = request.session.get('admin_type')
    if admin_type != 'admin':
        return JsonResponse({'error': 'Доступ запрещен'}, status=403)
    
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        
        if not student_id:
            return JsonResponse({'success': False, 'error': 'Не указан ID студента'}, status=400)
        
        student = get_object_or_404(Student, id=student_id)
        new_password = generate_password()
        student.password = new_password
        student.save()
        
        admin = get_admin_from_session(request)
        DatabaseLog.objects.create(
            user_id=admin.id if admin else None,
            user_type=admin.user_type if admin else None,
            user_name=admin.full_name if admin else 'Система',
            action='update',
            model_name='Student',
            object_id=student.id,
            details={'action': 'password_changed', 'new_password': new_password},
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return JsonResponse({
            'success': True,
            'new_password': new_password,
            'student_name': student.full_name
        })
        
    except Student.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Студент не найден'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Неверный формат JSON'}, status=400)
    except Exception as e:
        print(f"Ошибка в generate_and_set_password: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ==================== ЛОГИ ====================

@login_required_custom
def get_action_logs(request):
    """Получение расширенных логов действий"""
    logs = DatabaseLog.objects.all()[:100]
    
    data = [{
        'id': log.id,
        'user': log.user_name or 'Система',
        'action': log.get_action_display(),
        'model': log.model_name,
        'details': log.details,
        'ip': log.ip_address,
        'time': log.created_at.strftime('%d.%m.%Y %H:%M:%S')
    } for log in logs]
    
    return JsonResponse({'logs': data})

@login_required_custom
def clear_cache(request):
    """Очистка кэша действий"""
    if request.method == 'POST':
        try:
            threshold = timezone.now() - timedelta(days=30)
            ActionCache.objects.filter(
                is_restored=True,
                created_at__lt=threshold
            ).delete()
            
            admin = get_admin_from_session(request)
            DatabaseLog.objects.create(
                user_id=admin.id if admin else None,
                user_type=admin.user_type if admin else None,
                user_name=admin.full_name if admin else 'Система',
                action='clear_cache',
                model_name='ActionCache',
                details={'cleared': True},
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required_custom
@csrf_exempt
def restore_item(request):
    """Восстановление элемента из корзины"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cache_id = data.get('cache_id')
            admin = get_admin_from_session(request)
            
            deleted_item = get_object_or_404(DeletedItemCache, id=cache_id, is_restored=False)
            
            if deleted_item.item_type == 'student':
                student_data = deleted_item.item_data
                student = Student.objects.create(
                    login=student_data['login'],
                    full_name=student_data['full_name'],
                    email=student_data.get('email', ''),
                    phone=student_data.get('phone', ''),
                    group_id=student_data.get('group_id'),
                    user_type=student_data.get('user_type', 'student'),
                    is_elder=student_data.get('is_elder', False),
                    is_active=True
                )
                
                deleted_item.is_restored = True
                deleted_item.save()
                
                DatabaseLog.objects.create(
                    user_id=admin.id if admin else None,
                    user_type=admin.user_type if admin else None,
                    user_name=admin.full_name if admin else 'Система',
                    action='restore',
                    model_name='Student',
                    object_id=student.id,
                    details={'student': student.full_name},
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                return JsonResponse({'success': True, 'id': student.id})
                
            return JsonResponse({'success': False, 'error': 'Невозможно восстановить'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required_custom
def get_trash(request):
    """Получение содержимого корзины"""
    try:
        threshold = timezone.now() - timedelta(days=30)
        trash_items = DeletedItemCache.objects.filter(
            deleted_at__gte=threshold,
            is_restored=False
        )[:100]
        
        data = [{
            'id': item.id,
            'type': item.item_type,
            'data': item.item_data,
            'deleted_at': item.deleted_at.strftime('%d.%m.%Y %H:%M'),
            'expires_at': item.expires_at.strftime('%d.%m.%Y'),
            'deleted_by': item.user.username if item.user else 'Неизвестно'
        } for item in trash_items]
        
        return JsonResponse({'items': data})
    except Exception as e:
        return JsonResponse({'error': str(e), 'items': []}, status=500)