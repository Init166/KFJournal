from django.db import models 
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from admin_panel.models import Student, Group, ElderPermission
from students.models import StudentProfile, StudentGrade, Subject, Schedule, ScheduleComment, StudentPerformance, Attendance, SeminarSlot 
from .utils import get_week_type_for_date, get_current_week_type
import json
import random
import string
from datetime import datetime, timedelta

# ==================== ДЕКОРАТОР ДЛЯ ПРОВЕРКИ ПРАВ СТАРОСТЫ ====================

def elder_required(view_func):
    """Декоратор для проверки прав старосты"""
    def wrapper(request, *args, **kwargs):
        elder_id = request.session.get('elder_id')
        if not elder_id:
            return redirect('elder_login')
        try:
            elder = Student.objects.get(id=elder_id)
            # Проверяем, что пользователь действительно староста
            if elder.user_type != 'elder' and not elder.is_elder:
                return redirect('elder_login')
            request.elder = elder
            request.group = elder.group
            return view_func(request, *args, **kwargs)
        except Student.DoesNotExist:
            return redirect('elder_login')
    return wrapper

# ==================== АВТОРИЗАЦИЯ ====================

def elder_login(request):
    """Страница входа для старост"""
    error = None
    
    if request.method == 'POST':
        login_input = request.POST.get('login')
        password_input = request.POST.get('password')
        
        print(f"Попытка входа старосты: {login_input}")
        
        try:
            # Ищем студента по логину (как в admin_login)
            student = Student.objects.get(login=login_input)
            print(f"Найден студент: {student.full_name}, user_type: {student.user_type}, is_elder: {student.is_elder}")
            
            # Проверяем пароль (простое сравнение, как в admin_login)
            if student.password != password_input:
                error = 'Неверный пароль'
                print("Неверный пароль")
            # Проверяем, что это староста (user_type='elder' ИЛИ is_elder=True)
            elif student.user_type != 'elder' and not student.is_elder:
                error = 'У вас нет прав старосты'
                print("Не староста")
            else:
                # Всё хорошо - пускаем
                print("Вход разрешен")
                request.session['elder_id'] = student.id
                request.session['elder_name'] = student.full_name
                request.session['elder_group_id'] = student.group.id if student.group else None
                request.session['elder_group_name'] = student.group.name if student.group else None
                
                # Проверяем/создаем профиль студента
                StudentProfile.objects.get_or_create(
                    user=student,
                    defaults={
                        'group': student.group,
                        'total_hours': 0,
                        'remaining_hours': 20
                    }
                )
                
                return redirect('elder_dashboard')
                
        except Student.DoesNotExist:
            error = 'Пользователь не найден'
            print("Пользователь не найден")
    
    return render(request, 'elders/login.html', {'error': error})

def elder_logout(request):
    """Выход старосты"""
    request.session.flush()
    return redirect('elder_login')

# ==================== ЛИЧНЫЙ КАБИНЕТ СТАРОСТЫ ====================


@elder_required
def elder_dashboard(request):
    """Панель управления старосты"""
    students = request.group.students.all() if request.group else []
    students_count = students.count()
    
    # Общая статистика пропусков
    total_absences = 0
    for student in students:
        profile = StudentProfile.objects.get_or_create(user=student)[0]
        total_absences += profile.total_hours
    
    # Последние 5 добавленных студентов
    recent_students = students.order_by('-created_at')[:5]
    for student in recent_students:
        student.profile = StudentProfile.objects.get_or_create(user=student)[0]
    
    # Количество предметов
    subjects_count = StudentGrade.objects.filter(
        student__group=request.group
    ).values_list('subject', flat=True).distinct().count()
    
    context = {
        'elder': request.elder,
        'group': request.group,
        'students_count': students_count,
        'total_absences': total_absences,
        'recent_students': recent_students,
        'subjects_count': subjects_count,
    }
    
    return render(request, 'elders/dashboard.html', context)


@elder_required
def api_get_schedule(request):
    """Получение расписания"""
    week_type = request.GET.get('week_type')
    group_id = request.GET.get('group_id')
    
    schedule = Schedule.objects.filter(
        group_id=group_id,
        week_type__in=[week_type, 'both']
    ).order_by('day', 'pair_number')
    
    data = [{
        'id': s.id,
        'day': s.day,
        'pair_number': s.pair_number,
        'start_time': s.start_time,
        'end_time': s.end_time,
        'subject': s.subject,
        'teacher': s.teacher,
        'room': s.room,
        'lesson_type': s.lesson_type
    } for s in schedule]
    
    return JsonResponse({'schedule': data})

@elder_required
@csrf_exempt
@require_http_methods(["POST"])
def api_add_lesson(request):
    """Добавление занятия"""
    try:
        data = json.loads(request.body)
        
        # Проверяем, существует ли уже такая пара
        existing_lesson = Schedule.objects.filter(
            group_id=data['group_id'],
            day=data['day'],
            week_type=data['week_type'],
            pair_number=data['pair_number']
        ).first()
        
        if existing_lesson:
            return JsonResponse({
                'success': False, 
                'error': f'Пара на {dict(Schedule.DAYS_OF_WEEK)[data["day"]]} {data["pair_number"]} пара уже существует'
            }, status=400)
        
        lesson = Schedule.objects.create(
            group_id=data['group_id'],
            day=data['day'],
            week_type=data['week_type'],
            pair_number=data['pair_number'],
            start_time=data.get('start_time', '9:40'),
            end_time=data.get('end_time', '11:10'),
            subject=data['subject'],
            teacher=data.get('teacher', ''),
            room=data.get('room', ''),
            lesson_type=data.get('lesson_type', 'lecture')
        )
        
        # Создаем или обновляем предмет в списке предметов группы
        Subject.objects.get_or_create(
            name=data['subject'],
            group_id=data['group_id'],
            defaults={'teacher': data.get('teacher', '')}
        )
        
        return JsonResponse({'success': True, 'id': lesson.id})
        
    except Exception as e:
        print(f"Error in api_add_lesson: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@elder_required
@csrf_exempt
@require_http_methods(["POST"])
def api_update_lesson(request):
    """Обновление занятия"""
    try:
        data = json.loads(request.body)
        lesson = get_object_or_404(Schedule, id=data['id'], group=request.group)
        
        lesson.day = data['day']
        lesson.week_type = data['week_type']
        lesson.pair_number = data['pair_number']
        lesson.start_time = data['start_time']
        lesson.end_time = data['end_time']
        lesson.subject = data['subject']
        lesson.teacher = data.get('teacher', '')
        lesson.room = data.get('room', '')
        lesson.lesson_type = data.get('lesson_type', 'lecture')
        lesson.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@elder_required
def api_get_lesson(request, lesson_id):
    """Получение данных занятия"""
    lesson = get_object_or_404(Schedule, id=lesson_id, group=request.group)
    return JsonResponse({
        'id': lesson.id,
        'day': lesson.day,
        'pair_number': lesson.pair_number,
        'start_time': lesson.start_time,
        'end_time': lesson.end_time,
        'subject': lesson.subject,
        'teacher': lesson.teacher,
        'room': lesson.room,
        'lesson_type': lesson.lesson_type
    })



@elder_required
def elder_schedule(request):
    """Управление расписанием"""
    # Получаем дату из параметров или используем текущую
    date_str = request.GET.get('date')
    if date_str:
        try:
            current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            current_date = datetime.now().date()
    else:
        current_date = datetime.now().date()
    
    week_type = get_week_type_for_date(current_date)
    week_display = 'Чётная' if week_type == 'even' else 'Нечётная'
    
    days = [
        (1, 'Пн'), (2, 'Вт'), (3, 'Ср'), (4, 'Чт'), 
        (5, 'Пт'), (6, 'Сб'), (7, 'Вс')
    ]
    
    # Получаем все предметы группы для автодополнения
    subjects = Subject.objects.filter(group=request.group)
    
    # Получаем комментарии для этой недели
    comments = ScheduleComment.objects.filter(
        group=request.group,
        is_active=True
    ).order_by('-created_at')[:20]
    
    context = {
        'elder': request.elder,
        'group': request.group,
        'week_type': week_type,
        'week_display': week_display,
        'current_date': current_date,
        'days': days,
        'subjects': subjects,
        'comments': comments,
        'current_month': current_date.strftime('%B %Y'),
        'month_days': get_month_days(current_date.year, current_date.month),
    }
    return render(request, 'elders/schedule.html', context)

def get_month_days(year, month):
    """Возвращает список дней месяца с их типом недели"""
    from calendar import monthrange
    import calendar
    
    first_day, num_days = monthrange(year, month)
    
    # Переводим номер дня (0-6 понедельник-воскресенье) в наш формат (1-7)
    first_day = (first_day + 1) % 7
    if first_day == 0:
        first_day = 7
    
    days = []
    for day in range(1, num_days + 1):
        date = datetime(year, month, day).date()
        week_type = get_week_type_for_date(date)
        days.append({
            'day': day,
            'date': date,
            'week_type': week_type,
            'is_today': date == datetime.now().date()
        })
    
    return {
        'first_day': first_day,
        'days': days,
        'month_name': calendar.month_name[month],
        'year': year
    }


@elder_required
def elder_attendance(request):
    """Управление посещаемостью группы"""
    students = request.group.students.all().order_by('full_name') if request.group else []
    
    # Статистика по пропускам
    total_absences = 0
    at_risk_count = 0
    
    for student in students:
        profile = StudentProfile.objects.get_or_create(user=student)[0]
        total_absences += profile.total_hours
        if profile.total_hours >= 15:
            at_risk_count += 1
    
    context = {
        'elder': request.elder,
        'group': request.group,
        'students': students,
        'total_absences': total_absences,
        'at_risk_count': at_risk_count,
    }
    return render(request, 'elders/attendance.html', context)


@elder_required
def elder_grades(request):
    """Управление оценками группы"""
    # Получаем дату из параметров или используем текущую
    date_str = request.GET.get('date')
    if date_str:
        try:
            current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            current_date = datetime.now().date()
    else:
        current_date = datetime.now().date()
    
    week_type = get_week_type_for_date(current_date)
    week_display = 'Чётная' if week_type == 'even' else 'Нечётная'
    
    students = request.group.students.all().order_by('full_name') if request.group else []
    students_count = students.count()
    
    # Добавляем студентам дополнительные атрибуты
    for student in students:
        # Количество предметов, по которым есть оценки
        student.subjects_count = StudentGrade.objects.filter(
            student=student
        ).values_list('subject', flat=True).distinct().count()
        
        # Средний прогресс по всем предметам
        performances = StudentPerformance.objects.filter(student=student)
        if performances.exists():
            total_progress = 0
            for p in performances:
                # Вычисляем прогресс вручную, если свойство не работает
                progress = (p.total_points / p.target_points) * 100 if p.target_points else 0
                total_progress += min(100, progress)
            student.avg_progress = round(total_progress / performances.count(), 1)
        else:
            student.avg_progress = 0
    
    # Статистика по успеваемости
    at_risk_count = 0
    ready_count = 0
    
    for student in students:
        performances = StudentPerformance.objects.filter(student=student)
        student_at_risk = False
        student_ready = True
        
        for perf in performances:
            if perf.total_points < 15:
                student_at_risk = True
            if perf.total_points < 21:
                student_ready = False
        
        if student_at_risk:
            at_risk_count += 1
        if student_ready and performances.exists():
            ready_count += 1
    
    # Получаем все предметы группы
    subjects = Subject.objects.filter(group=request.group)
    
    # Данные для календаря
    month_days = get_month_days(current_date.year, current_date.month)
    
    context = {
        'elder': request.elder,
        'group': request.group,
        'students': students,
        'students_count': students_count,
        'at_risk_count': at_risk_count,
        'ready_count': ready_count,
        'subjects': subjects,
        'week_type': week_type,
        'week_display': week_display,
        'current_date': current_date,
        'month_days': month_days,
    }
    return render(request, 'elders/grades_new.html', context)


@elder_required
def elder_students(request):
    """Просмотр и управление студентами группы"""
    students = request.group.students.all().order_by('full_name') if request.group else []
    
    # Добавляем информацию о профилях
    for student in students:
        profile = StudentProfile.objects.get_or_create(user=student)[0]
        student.profile = profile
    
    context = {
        'elder': request.elder,
        'group': request.group,
        'students': students,
    }
    return render(request, 'elders/students.html', context)

# ==================== УПРАВЛЕНИЕ СТУДЕНТАМИ ====================

@elder_required
@csrf_exempt
@require_http_methods(["POST"])
def api_add_student(request):
    """Добавление нового студента в группу старосты"""
    try:
        # Получаем данные из формы
        full_name = request.POST.get('full_name')
        login = request.POST.get('login')
        password = request.POST.get('password')
        
        # Проверяем, что все поля заполнены
        if not all([full_name, login, password]):
            return JsonResponse({'success': False, 'error': 'Заполните все поля'}, status=400)
        
        # Проверяем уникальность логина
        if Student.objects.filter(login=login).exists():
            return JsonResponse({'success': False, 'error': 'Логин уже существует'}, status=400)
        
        # Проверяем лимит студентов (если есть в правах)
        try:
            permissions = request.elder.permissions
            if permissions.max_students:
                current_count = request.group.students.count()
                if current_count >= permissions.max_students:
                    return JsonResponse({'success': False, 'error': f'Достигнут лимит студентов ({permissions.max_students})'}, status=400)
        except (ElderPermission.DoesNotExist, AttributeError):
            pass  # Нет прав или ограничений
        
        # Создаем студента
        student = Student.objects.create(
            login=login,
            password=password,  # Храним как есть, как в admin_panel
            full_name=full_name,
            group=request.group,
            user_type='student',
            is_elder=False,
            is_active=True
        )
        
        # Создаем профиль студента
        StudentProfile.objects.create(
            user=student,
            group=request.group,
            total_hours=0,
            remaining_hours=20
        )
        
        return JsonResponse({
            'success': True,
            'student': {
                'id': student.id,
                'full_name': student.full_name,
                'login': student.login,
                'password': student.password
            }
        })
        
    except Exception as e:
        print(f"Ошибка при добавлении студента: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@elder_required
@csrf_exempt
@require_http_methods(["POST"])
def api_update_student_password(request):
    """Обновление пароля студента"""
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        new_password = data.get('password')
        
        student = get_object_or_404(Student, id=student_id, group=request.group)
        student.password = new_password
        student.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@elder_required
@csrf_exempt
@require_http_methods(["POST"])
def api_delete_student(request):
    """Удаление студента"""
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        
        student = get_object_or_404(Student, id=student_id, group=request.group)
        
        # Удаляем связанные данные
        StudentProfile.objects.filter(user=student).delete()
        StudentGrade.objects.filter(student=student).delete()
        
        # Удаляем студента
        student.delete()
        
        return JsonResponse({'success': True})
        
    except Student.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Студент не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@elder_required
def api_generate_password(request):
    """Генерация случайного пароля"""
    chars = string.ascii_letters + string.digits
    password = ''.join(random.choice(chars) for _ in range(8))
    return JsonResponse({'password': password})

# ==================== ПАРОЛИ =======================

@elder_required
def elder_view_passwords(request):
    """Староста видит пароли только своей группы"""
    students = Student.objects.filter(group=request.group).select_related('group')
    
    data = [{
        'id': s.id,
        'login': s.login,
        'password': s.password,
        'full_name': s.full_name,
        'user_type': s.get_user_type_display(),
        'is_active': s.is_active
    } for s in students]
    
    return JsonResponse({'passwords': data})

# ==================== API ДЛЯ ОЦЕНОК ====================


@elder_required
@csrf_exempt
@require_http_methods(["POST"])
def api_add_grade(request):
    """Добавление оценки студенту"""
    try:
        data = json.loads(request.body)
        print(f"Grade data received: {data}")  # Отладка
        
        student_id = data.get('student_id')
        subject_id = data.get('subject_id')
        
        if not student_id or not subject_id:
            return JsonResponse({'success': False, 'error': 'Missing student_id or subject_id'}, status=400)
        
        student = get_object_or_404(Student, id=student_id, group=request.group)
        subject = get_object_or_404(Subject, id=subject_id, group=request.group)
        
        # Обработка даты
        use_today = data.get('use_today') == 'true'
        if use_today:
            grade_date = datetime.now().date()
        else:
            try:
                grade_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            except:
                grade_date = datetime.now().date()
        
        # Создаем оценку
        grade = StudentGrade.objects.create(
            student=student,
            subject=subject,
            group=request.group,
            grade_type=data['grade_type'],
            raw_value=data.get('raw_value', data['grade_type']),
            date=grade_date,
            is_today=use_today,
            marked_by=request.elder,
            comment=data.get('comment', '')
        )
        
        # Обновляем StudentPerformance
        performance, created = StudentPerformance.objects.get_or_create(
            student=student,
            subject=subject,
            defaults={'total_points': 0}
        )
        
        # Пересчитываем общие баллы
        total_points = StudentGrade.objects.filter(
            student=student,
            subject=subject
        ).aggregate(total=models.Sum('points'))['total'] or 0
        
        performance.total_points = total_points
        performance.save()
        
        return JsonResponse({
            'success': True,
            'grade': {
                'id': grade.id,
                'value': grade.raw_value,
                'points': grade.points,
                'total': total_points
            }
        })
        
    except Exception as e:
        print(f"Error in api_add_grade: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@elder_required
@csrf_exempt
@require_http_methods(["POST"])
def api_delete_grade(request):
    """Удаление оценки"""
    try:
        data = json.loads(request.body)
        grade_id = data.get('grade_id')
        
        grade = get_object_or_404(StudentGrade, id=grade_id, student__group=request.group)
        grade.delete()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ==================== API ДЛЯ ПРОПУСКОВ ====================



@elder_required
@csrf_exempt
@require_http_methods(["POST"])
def api_add_attendance(request):
    """Добавление пропуска"""
    try:
        data = json.loads(request.body)
        
        student = get_object_or_404(Student, id=data['student_id'], group=request.group)
        
        # Создаем запись о пропуске
        attendance = Attendance.objects.create(
            student=student,
            group=request.group,
            date=data['date'],
            hours=data['hours'],
            reason=data.get('reason', ''),
            marked_by=request.elder
        )
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        print(f"Error adding attendance: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@elder_required
@csrf_exempt
@require_http_methods(["POST"])
def api_delete_lesson(request):
    """Удаление занятия из расписания"""
    try:
        data = json.loads(request.body)
        lesson_id = data.get('id')
        
        lesson = get_object_or_404(Schedule, id=lesson_id, group=request.group)
        lesson.delete()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@elder_required
def api_get_lesson(request, lesson_id):
    """Получение данных конкретного занятия"""
    try:
        lesson = get_object_or_404(Schedule, id=lesson_id, group=request.group)
        
        data = {
            'id': lesson.id,
            'day': lesson.day,
            'week_type': lesson.week_type,
            'pair_number': lesson.pair_number,
            'start_time': lesson.start_time,
            'end_time': lesson.end_time,
            'subject': lesson.subject,
            'teacher': lesson.teacher or '',
            'room': lesson.room or '',
            'lesson_type': lesson.lesson_type
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@elder_required
def api_get_schedule(request):
    """Получение расписания для отображения"""
    try:
        week_type = request.GET.get('week_type')
        group_id = request.GET.get('group_id')
        
        if not week_type or not group_id:
            return JsonResponse({'error': 'Missing parameters'}, status=400)
        
        schedule = Schedule.objects.filter(
            group_id=group_id,
            week_type__in=[week_type, 'both']
        ).order_by('day', 'pair_number')
        
        data = [{
            'id': s.id,
            'day': s.day,
            'pair_number': s.pair_number,
            'start_time': s.start_time,
            'end_time': s.end_time,
            'subject': s.subject,
            'teacher': s.teacher or '',
            'room': s.room or '',
            'lesson_type': s.get_lesson_type_display() if hasattr(s, 'get_lesson_type_display') else s.lesson_type
        } for s in schedule]
        
        return JsonResponse({'schedule': data})
        
    except Exception as e:
        return JsonResponse({'error': str(e), 'schedule': []}, status=500)

@elder_required
@csrf_exempt
@require_http_methods(["POST"])
def api_add_lesson(request):
    """Добавление нового занятия"""
    try:
        data = json.loads(request.body)
        
        # Проверяем обязательные поля
        required_fields = ['day', 'week_type', 'group_id', 'pair_number', 'subject']
        for field in required_fields:
            if field not in data:
                return JsonResponse({'success': False, 'error': f'Missing field: {field}'}, status=400)
        
        # Создаем занятие
        lesson = Schedule.objects.create(
            group_id=data['group_id'],
            day=data['day'],
            week_type=data['week_type'],
            pair_number=data['pair_number'],
            start_time=data.get('start_time', '9:40'),
            end_time=data.get('end_time', '11:10'),
            subject=data['subject'],
            teacher=data.get('teacher', ''),
            room=data.get('room', ''),
            lesson_type=data.get('lesson_type', 'lecture')
        )
        
        # Создаем или обновляем предмет в списке предметов группы
        Subject.objects.get_or_create(
            name=data['subject'],
            group_id=data['group_id'],
            defaults={'teacher': data.get('teacher', '')}
        )
        
        return JsonResponse({'success': True, 'id': lesson.id})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@elder_required
@csrf_exempt
@require_http_methods(["POST"])
def api_update_lesson(request):
    """Обновление существующего занятия"""
    try:
        data = json.loads(request.body)
        
        if 'id' not in data:
            return JsonResponse({'success': False, 'error': 'Missing lesson id'}, status=400)
        
        lesson = get_object_or_404(Schedule, id=data['id'], group=request.group)
        
        # Обновляем поля
        if 'day' in data:
            lesson.day = data['day']
        if 'week_type' in data:
            lesson.week_type = data['week_type']
        if 'pair_number' in data:
            lesson.pair_number = data['pair_number']
        if 'start_time' in data:
            lesson.start_time = data['start_time']
        if 'end_time' in data:
            lesson.end_time = data['end_time']
        if 'subject' in data:
            lesson.subject = data['subject']
        if 'teacher' in data:
            lesson.teacher = data['teacher']
        if 'room' in data:
            lesson.room = data['room']
        if 'lesson_type' in data:
            lesson.lesson_type = data['lesson_type']
        
        lesson.save()
        
        # Обновляем или создаем предмет
        Subject.objects.get_or_create(
            name=lesson.subject,
            group=request.group,
            defaults={'teacher': lesson.teacher}
        )
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@elder_required
@csrf_exempt
@require_http_methods(["POST"])
def api_copy_schedule(request):
    """Копирование расписания с другой недели"""
    try:
        data = json.loads(request.body)
        from_week = data.get('from_week')
        to_week = data.get('to_week')
        
        if not from_week or not to_week:
            return JsonResponse({'success': False, 'error': 'Missing week parameters'}, status=400)
        
        # Удаляем существующее расписание на целевой неделе
        Schedule.objects.filter(group=request.group, week_type=to_week).delete()
        
        # Копируем с исходной недели
        source_schedule = Schedule.objects.filter(group=request.group, week_type=from_week)
        
        for lesson in source_schedule:
            Schedule.objects.create(
                group=request.group,
                day=lesson.day,
                week_type=to_week,
                pair_number=lesson.pair_number,
                start_time=lesson.start_time,
                end_time=lesson.end_time,
                subject=lesson.subject,
                teacher=lesson.teacher,
                room=lesson.room,
                lesson_type=lesson.lesson_type
            )
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@elder_required
@csrf_exempt
@require_http_methods(["POST"])
def api_reset_attendance(request):
    """Сброс всех пропусков группы"""
    try:
        students = request.group.students.all()
        StudentProfile.objects.filter(user__in=students).update(
            total_hours=0,
            remaining_hours=20
        )
        
        # TODO: удалить или архивировать историю пропусков
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ==================== API ДЛЯ ПРИОРИТЕТОВ ====================

@elder_required
def api_get_priority(request):
    """Получение приоритетов по предмету"""
    subject = request.GET.get('subject')
    if not subject:
        return JsonResponse({'error': 'Subject required'}, status=400)
    
    students = request.group.students.all()
    priority_data = []
    
    for student in students:
        grades = StudentGrade.objects.filter(student=student, subject=subject)
        profile = StudentProfile.objects.get_or_create(user=student)[0]
        
        # Считаем сумму баллов
        total_score = 0
        grade_count = 0
        grades_list = []
        
        for grade in grades:
            grades_list.append(grade.grade)
            try:
                # Пытаемся преобразовать в число (с учетом + и -)
                grade_value = grade.grade
                if grade_value.replace('+', '').replace('-', '').replace('.', '').isdigit():
                    if grade_value.endswith('+'):
                        total_score += float(grade_value[:-1]) + 0.3
                    elif grade_value.endswith('-'):
                        total_score += float(grade_value[:-1]) - 0.3
                    else:
                        total_score += float(grade_value)
                    grade_count += 1
            except ValueError:
                pass
        
        total_score = round(total_score, 2)
        remaining = max(0, 21 - total_score)
        progress = (total_score / 21) * 100 if total_score > 0 else 0
        
        priority_data.append({
            'student_id': student.id,
            'student_name': student.full_name,
            'grade_count': grade_count,
            'grades': ', '.join(grades_list) if grades_list else '—',
            'total_score': total_score,
            'progress': round(progress, 1),
            'remaining': round(remaining, 1),
            'absence_hours': profile.total_hours,
            'status': 'danger' if total_score < 8 else 'warning' if total_score < 14 else 'success'
        })
    
    # Сортируем по убыванию оставшихся баллов (кто больше всего отстает)
    priority_data.sort(key=lambda x: x['remaining'], reverse=True)
    
    return JsonResponse({'priority': priority_data, 'subject': subject})

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_week_type(date):
    """Определение типа недели (четная/нечетная)"""
    start_date = datetime(2024, 1, 1).date()
    days_diff = (date - start_date).days
    week_number = days_diff // 7
    return 'even' if week_number % 2 == 0 else 'odd'


@elder_required
def api_get_subjects(request):
    """Получение списка предметов группы"""
    subjects = Subject.objects.filter(group=request.group, is_active=True)
    
    data = [{
        'id': s.id,
        'name': s.name,
        'teacher': s.teacher
    } for s in subjects]
    
    return JsonResponse({'subjects': data})

@elder_required
def api_get_students_with_performance(request):
    """Получение студентов с их успеваемостью по предмету"""
    subject_id = request.GET.get('subject_id')
    subject = get_object_or_404(Subject, id=subject_id, group=request.group)
    
    students = request.group.students.filter(is_active=True).order_by('full_name')
    
    data = []
    for student in students:
        performance, _ = StudentPerformance.objects.get_or_create(
            student=student,
            subject=subject,
            defaults={'total_points': 0}
        )
        
        grades = StudentGrade.objects.filter(
            student=student,
            subject=subject
        ).order_by('-date')[:10]
        
        data.append({
            'id': student.id,
            'name': student.full_name,
            'total_points': performance.total_points,
            'remaining': performance.remaining_points,
            'progress': performance.progress_percentage,
            'status': performance.status,
            'grades': [{
                'id': g.id,
                'value': g.raw_value,
                'points': g.points,
                'date': g.date.strftime('%d.%m.%Y'),
                'type': g.get_grade_type_display()
            } for g in grades]
        })
    
    return JsonResponse({'students': data})


@elder_required
@csrf_exempt
@require_http_methods(["POST"])
def api_delete_grade(request):
    """Удаление оценки"""
    try:
        data = json.loads(request.body)
        grade_id = data.get('id')
        
        grade = get_object_or_404(StudentGrade, id=grade_id, student__group=request.group)
        grade.delete()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ==================== API ДЛЯ КОММЕНТАРИЕВ ====================
@elder_required
@csrf_exempt
@require_http_methods(["POST"])
def api_add_comment(request):
    """Добавление комментария к расписанию"""
    try:
        data = json.loads(request.body)
        print("Received comment data:", data)  # Отладка
        
        comment = ScheduleComment.objects.create(
            group=request.group,
            comment=data['comment'],
            week_type=data.get('week_type'),
            day=data.get('day'),
            date=data.get('date'),
            is_urgent=data.get('is_urgent', False),
            created_by=request.elder
        )
        
        return JsonResponse({'success': True, 'id': comment.id})
        
    except Exception as e:
        print("Error adding comment:", str(e))  # Отладка
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@elder_required
def api_get_comments(request):
    """Получение комментариев"""
    try:
        week_type = request.GET.get('week_type')
        
        comments = ScheduleComment.objects.filter(
            group=request.group,
            is_active=True
        ).order_by('-created_at')
        
        if week_type:
            comments = comments.filter(
                models.Q(week_type=week_type) |
                models.Q(week_type__isnull=True)
            )
        
        data = [{
            'id': c.id,
            'text': c.comment,
            'week_type': c.week_type,
            'day': c.day,
            'date': c.date.strftime('%Y-%m-%d') if c.date else None,
            'is_urgent': c.is_urgent,
            'author': c.created_by.full_name if c.created_by else 'Система',
            'created_time': c.created_at.strftime('%H:%M %d.%m.%Y')
        } for c in comments]
        
        return JsonResponse({'comments': data})
        
    except Exception as e:
        print("Error getting comments:", str(e))
        return JsonResponse({'error': str(e), 'comments': []}, status=500)


@elder_required
@csrf_exempt
@require_http_methods(["POST"])
def api_delete_comment(request):
    """Удаление комментария"""
    try:
        data = json.loads(request.body)
        comment_id = data.get('id')
        
        comment = get_object_or_404(ScheduleComment, id=comment_id, group=request.group)
        comment.is_active = False
        comment.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@elder_required
def api_attendance_history(request):
    """Получение истории пропусков студента"""
    student_id = request.GET.get('student_id')
    student = get_object_or_404(Student, id=student_id, group=request.group)
    
    attendances = Attendance.objects.filter(student=student).order_by('-date')
    profile = StudentProfile.objects.get_or_create(user=student)[0]
    
    data = [{
        'id': a.id,
        'date': a.date.strftime('%d.%m.%Y'),
        'hours': a.hours,
        'reason': a.reason,
        'marked_by': a.marked_by.full_name if a.marked_by else 'Система'
    } for a in attendances]
    
    return JsonResponse({
        'history': data,
        'total': profile.total_hours
    })

@elder_required
@csrf_exempt
@require_http_methods(["POST"])
def api_delete_attendance(request):
    """Удаление записи о пропуске"""
    try:
        data = json.loads(request.body)
        attendance = get_object_or_404(Attendance, id=data['id'], student__group=request.group)
        
        # Обновляем профиль
        profile = StudentProfile.objects.get_or_create(user=attendance.student)[0]
        profile.total_hours -= attendance.hours
        profile.remaining_hours = max(0, 20 - profile.total_hours)
        profile.save()
        
        attendance.delete()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@elder_required
def api_seminar_slots(request):
    """Получение семинаров со слотами"""
    week_type = request.GET.get('week_type')
    group_id = request.GET.get('group_id')
    
    seminars = Schedule.objects.filter(
        group_id=group_id,
        week_type__in=[week_type, 'both'],
        lesson_type='seminar'
    ).order_by('day', 'pair_number')
    
    data = []
    for seminar in seminars:
        slots = SeminarSlot.objects.filter(schedule=seminar)
        slots_data = []
        for slot in slots:
            student_points = 0
            if slot.student:
                try:
                    subject = Subject.objects.get(name=seminar.subject, group=request.group)
                    performance = StudentPerformance.objects.get(student=slot.student, subject=subject)
                    student_points = performance.total_points
                except:
                    pass
            
            slots_data.append({
                'id': slot.id,
                'slot_number': slot.slot_number,
                'student_id': slot.student.id if slot.student else None,
                'student_name': slot.student.full_name if slot.student else None,
                'student_points': student_points
            })
        
        data.append({
            'id': seminar.id,
            'day': seminar.day,
            'start_time': seminar.start_time,
            'end_time': seminar.end_time,
            'subject': seminar.subject,
            'teacher': seminar.teacher,
            'slots': slots_data
        })
    
    return JsonResponse({'seminars': data})

@elder_required
def api_students_with_points(request):
    """Список студентов с их баллами по предмету"""
    subject_id = request.GET.get('subject_id')
    
    if not subject_id:
        return JsonResponse({'students': []})
    
    try:
        subject = Subject.objects.get(id=subject_id, group=request.group)
    except Subject.DoesNotExist:
        return JsonResponse({'students': []})
    
    students = request.group.students.filter(is_active=True).order_by('full_name')
    
    data = []
    for student in students:
        performance, _ = StudentPerformance.objects.get_or_create(
            student=student,
            subject=subject,
            defaults={'total_points': 0}
        )
        data.append({
            'id': student.id,
            'name': student.full_name,
            'total_points': performance.total_points
        })
    
    return JsonResponse({'students': data})


@elder_required
def api_student_points(request):
    """Получение баллов студента по предмету"""
    student_id = request.GET.get('student_id')
    subject_name = request.GET.get('subject')
    
    if not student_id or not subject_name:
        return JsonResponse({'total_points': 0})
    
    try:
        student = get_object_or_404(Student, id=student_id, group=request.group)
        subject = get_object_or_404(Subject, name=subject_name, group=request.group)
        
        performance, _ = StudentPerformance.objects.get_or_create(
            student=student,
            subject=subject,
            defaults={'total_points': 0}
        )
        
        return JsonResponse({'total_points': performance.total_points})
    except Exception as e:
        print(f"Error in api_student_points: {e}")
        return JsonResponse({'total_points': 0})

def get_subject_id(seminar_id):
    """Вспомогательная функция для получения ID предмета по ID семинара"""
    try:
        seminar = Schedule.objects.get(id=seminar_id)
        subject = Subject.objects.get(name=seminar.subject, group=seminar.group)
        return subject.id
    except:
        return None

@elder_required
def api_students_list(request):
    """Список студентов группы"""
    group_id = request.GET.get('group_id')
    students = Student.objects.filter(group_id=group_id, is_active=True).order_by('full_name')
    
    data = [{
        'id': s.id,
        'name': s.full_name
    } for s in students]
    
    return JsonResponse({'students': data})

@elder_required
@csrf_exempt
@require_http_methods(["POST"])
def api_assign_slot(request):
    """Назначение студента в слот"""
    try:
        data = json.loads(request.body)
        
        # Создаем слот, если его нет
        slot, created = SeminarSlot.objects.get_or_create(
            schedule_id=data['seminar_id'],
            slot_number=data['slot_number'],
            defaults={'student_id': data['student_id']}
        )
        
        if not created:
            slot.student_id = data['student_id']
            slot.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@elder_required
@csrf_exempt
@require_http_methods(["POST"])
def api_remove_slot(request):
    """Удаление студента из слота"""
    try:
        data = json.loads(request.body)
        slot = get_object_or_404(SeminarSlot, id=data['slot_id'], schedule__group=request.group)
        slot.student = None
        slot.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@elder_required
def api_get_subject_id(request):
    """Получение ID предмета по ID семинара"""
    seminar_id = request.GET.get('seminar_id')
    try:
        seminar = Schedule.objects.get(id=seminar_id, group=request.group)
        # Ищем предмет по названию и группе
        subject = Subject.objects.get(
            name=seminar.subject,
            group=request.group
        )
        return JsonResponse({'subject_id': subject.id})
    except (Schedule.DoesNotExist, Subject.DoesNotExist) as e:
        print(f"Error in api_get_subject_id: {e}")
        return JsonResponse({'subject_id': None, 'error': str(e)})

@elder_required
def student_detail(request, student_id):
    """Детальная страница студента с его успеваемостью"""
    student = get_object_or_404(Student, id=student_id, group=request.group)
    profile = StudentProfile.objects.get_or_create(user=student)[0]
    
    # Получаем все оценки студента
    grades = StudentGrade.objects.filter(student=student).select_related('subject').order_by('-date')
    
    # Группируем по предметам
    subjects_data = []
    for subject in Subject.objects.filter(group=request.group):
        subject_grades = grades.filter(subject=subject)
        performance, _ = StudentPerformance.objects.get_or_create(
            student=student,
            subject=subject,
            defaults={'total_points': 0}
        )
        
        subjects_data.append({
            'subject': subject,
            'grades': subject_grades,
            'total_points': performance.total_points,
            'progress': performance.progress_percentage,
            'remaining': performance.remaining_points,
            'status': performance.status
        })
    
    # Получаем слоты, где записан студент
    slots = SeminarSlot.objects.filter(
        student=student,
        schedule__week_type__in=[get_week_type_for_date(datetime.now().date()), 'both']
    ).select_related('schedule').order_by('schedule__day', 'schedule__pair_number')
    
    # Получаем пропуски
    attendances = Attendance.objects.filter(student=student).order_by('-date')
    
    context = {
        'elder': request.elder,
        'group': request.group,
        'student': student,
        'profile': profile,
        'subjects_data': subjects_data,
        'slots': slots,
        'attendances': attendances,
        'total_hours': profile.total_hours,
        'remaining_hours': profile.remaining_hours,
        # 'students': students,  # УДАЛИТЕ ЭТУ СТРОКУ - она лишняя!
    }
    
    return render(request, 'elders/student_detail.html', context)



@elder_required
def api_get_student(request, student_id):
    """Получение данных студента для редактирования"""
    try:
        student = get_object_or_404(Student, id=student_id, group=request.group)
        
        data = {
            'id': student.id,
            'full_name': student.full_name,
            'login': student.login,
            'password': student.password,
            'email': student.email or '',
            'phone': student.phone or '',
            'user_type': student.user_type,
            'is_active': student.is_active,
            'group_id': student.group.id if student.group else None,
            'group_name': student.group.name if student.group else 'Нет группы',
        }
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@elder_required
@csrf_exempt
@require_http_methods(["POST"])
def api_update_student(request):
    """Обновление данных студента"""
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        
        student = get_object_or_404(Student, id=student_id, group=request.group)
        
        # Обновляем поля
        student.full_name = data.get('full_name', student.full_name)
        student.login = data.get('login', student.login)
        student.password = data.get('password', student.password)
        student.email = data.get('email', student.email)
        student.phone = data.get('phone', student.phone)
        student.user_type = data.get('user_type', student.user_type)
        student.is_active = data.get('is_active') == 'true' or data.get('is_active') == True
        student.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)