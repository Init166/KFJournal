# students/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from admin_panel.models import Student, Group
from students.models import StudentProfile, StudentGrade, Subject, Schedule, ScheduleComment, Attendance, StudentPerformance
from datetime import datetime, timedelta
from django.db.models import Sum, Q
import json

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_week_type(target_date=None):
    """Определяет тип недели (чётная/нечётная)"""
    if target_date is None:
        target_date = datetime.today().date()
    
    # Используем ту же логику, что и в панели старосты
    start_date = datetime(2024, 9, 2).date()
    delta = target_date - start_date
    weeks_passed = delta.days // 7
    return "even" if weeks_passed % 2 == 1 else "odd"

# ==================== АВТОРИЗАЦИЯ ====================

def student_login(request):
    """Страница входа для студентов"""
    error = None
    
    if request.method == 'POST':
        login_input = request.POST.get('login')
        password_input = request.POST.get('password')
        
        try:
            student = Student.objects.get(login=login_input)
            if student.password == password_input:
                # Создаём сессию
                request.session['student_id'] = student.id
                request.session['student_name'] = student.full_name
                request.session['student_group_id'] = student.group.id if student.group else None
                request.session['student_group_name'] = student.group.name if student.group else None
                
                # Создаём или получаем профиль
                profile, created = StudentProfile.objects.get_or_create(
                    user=student,
                    defaults={'group': student.group}
                )
                
                return redirect('student_dashboard')
            else:
                error = 'Неверный пароль'
        except Student.DoesNotExist:
            error = 'Пользователь не найден'
    
    return render(request, 'students/login.html', {'error': error})

def student_logout(request):
    """Выход студента"""
    request.session.flush()
    return redirect('student_login')

# ==================== ЛИЧНЫЙ КАБИНЕТ ====================

def student_dashboard(request):
    """Личный кабинет студента"""
    student_id = request.session.get('student_id')
    if not student_id:
        return redirect('student_login')
    
    try:
        student = Student.objects.get(id=student_id)
        if not student.group:
            return render(request, 'students/dashboard.html', {
                'student': student,
                'error': 'У вас не назначена группа'
            })
        
        profile, created = StudentProfile.objects.get_or_create(
            user=student,
            defaults={'group': student.group}
        )
        
        # Получаем все оценки студента
        grades = StudentGrade.objects.filter(student=student).select_related('subject').order_by('-date')
        
        # Группируем оценки по предметам
        subjects = {}
        subject_totals = {}
        
        for grade in grades:
            if grade.subject not in subjects:
                subjects[grade.subject] = []
            subjects[grade.subject].append(grade)
        
        # Считаем баллы по каждому предмету
        for subject, grade_list in subjects.items():
            total = 0
            for g in grade_list:
                total += g.points  # Используем points вместо raw_value
            subject_totals[subject] = round(total, 2)
        
        # Статистика пропусков
        attendances = Attendance.objects.filter(student=student)
        total_hours = attendances.aggregate(total=Sum('hours'))['total'] or 0
        remaining = max(0, 20 - total_hours)
        
        # Последние 5 оценок для отображения
        recent_grades = grades[:10]
        
        # Проверяем, есть ли сегодня занятия
        today = datetime.now().date()
        week_type = get_week_type(today)
        today_schedule = Schedule.objects.filter(
            group=student.group,
            day=today.isoweekday(),
            week_type__in=[week_type, 'both']
        ).order_by('pair_number')
        
        context = {
            'student': student,
            'profile': profile,
            'grades': grades,
            'recent_grades': recent_grades,
            'subjects': subjects,
            'subject_totals': subject_totals,
            'total_hours': total_hours,
            'remaining': remaining,
            'progress': min(100, (total_hours / 20) * 100) if total_hours > 0 else 0,
            'today_schedule': today_schedule,
        }
        
        return render(request, 'students/dashboard.html', context)
        
    except Student.DoesNotExist:
        return redirect('student_login')

# ==================== РАСПИСАНИЕ ====================

def student_schedule(request):
    """Просмотр расписания с удобной навигацией"""
    student_id = request.session.get('student_id')
    if not student_id:
        return redirect('student_login')
    
    try:
        student = Student.objects.get(id=student_id)
        if not student.group:
            return render(request, 'students/schedule.html', {
                'error': 'У вас не назначена группа'
            })
        
        # Получаем текущую дату
        today = datetime.now().date()
        
        # Определяем тип текущей недели
        current_week_type = get_week_type(today)
        current_week_display = 'Чётная' if current_week_type == 'even' else 'Нечётная'
        
        # Определяем тип следующей недели
        next_week_type = 'even' if current_week_type == 'odd' else 'odd'
        next_week_display = 'Чётная' if next_week_type == 'even' else 'Нечётная'
        
        # ОТЛАДОЧНЫЙ КОД
        print(f"=== Отладка комментариев для студента {student.full_name} ===")
        print(f"Сегодня: {today}, день недели: {today.isoweekday()}, тип недели: {current_week_type}")
        
        # Проверим все комментарии группы
        all_comments = ScheduleComment.objects.filter(group=student.group, is_active=True)
        print(f"Всего комментариев в группе: {all_comments.count()}")
        
        for c in all_comments:
            print(f"Комментарий ID={c.id}: '{c.comment[:30]}...'")
            print(f"  date={c.date}, week_type={c.week_type}, day={c.day}, lesson_id={c.lesson_id}")
            print(f"  is_urgent={c.is_urgent}, created={c.created_at}")
        
        # ПОЛУЧАЕМ КОММЕНТАРИИ - ИСПРАВЛЕННАЯ ЛОГИКА
        comments = ScheduleComment.objects.filter(
            group=student.group,
            is_active=True
        ).filter(
            # 1. Комментарии на конкретную дату (сегодня)
            Q(date=today) |
            # 2. Комментарии на сегодняшний день недели (ЛЮБОЙ тип недели)
            Q(day=today.isoweekday(), date__isnull=True) |
            # 3. Комментарии на всю неделю (ЛЮБОЙ тип)
            Q(week_type__isnull=False, day__isnull=True, date__isnull=True) |
            # 4. Комментарии без привязки (общие)
            Q(week_type__isnull=True, day__isnull=True, date__isnull=True)
        ).order_by('-is_urgent', '-created_at')
        
        print(f"Комментариев после фильтрации: {comments.count()}")
        for c in comments:
            print(f"  Попал в фильтр: {c.id} - {c.comment[:30]}")
        
        # Также получаем комментарии для завтрашнего дня
        tomorrow = today + timedelta(days=1)
        
        tomorrow_comments = ScheduleComment.objects.filter(
            group=student.group,
            is_active=True
        ).filter(
            Q(date=tomorrow) |
            Q(day=tomorrow.isoweekday(), date__isnull=True)
        ).order_by('-is_urgent', '-created_at')
        
        # Проверяем, есть ли комментарии на сегодня
        today_comments = comments.filter(
            Q(date=today) |
            Q(day=today.isoweekday(), date__isnull=True)
        )
        
        # Расписание на сегодня
        today_schedule = Schedule.objects.filter(
            group=student.group,
            day=today.isoweekday(),
            week_type__in=[current_week_type, 'both']
        ).order_by('pair_number')
        
        # Для каждой пары в today_schedule проверяем, есть ли комментарии
        for lesson in today_schedule:
            # Комментарии конкретно к этой паре (если lesson_id указан)
            lesson_comments = ScheduleComment.objects.filter(
                group=student.group,
                is_active=True,
                lesson=lesson
            ).order_by('-created_at')
            
            # Сохраняем комментарии как атрибут объекта
            setattr(lesson, 'lesson_comments', lesson_comments)
            setattr(lesson, 'has_comments', lesson_comments.exists())
        
        # Расписание на завтра
        tomorrow_schedule = Schedule.objects.filter(
            group=student.group,
            day=tomorrow.isoweekday(),
            week_type__in=[current_week_type, 'both']  # ИСПРАВЛЕНО: используем current_week_type вместо tomorrow_week_type
        ).order_by('pair_number')
        
        # Расписание на текущую неделю
        current_week_schedule = Schedule.objects.filter(
            group=student.group,
            week_type__in=[current_week_type, 'both']
        ).order_by('day', 'pair_number')
        
        # Расписание на следующую неделю
        next_week_schedule = Schedule.objects.filter(
            group=student.group,
            week_type__in=[next_week_type, 'both']
        ).order_by('day', 'pair_number')
        
        # Данные для календаря
        month_days = get_month_days(today.year, today.month)
        
        # Добавляем к каждому дню календаря комментарии
        for day_data in month_days['days']:
            day_date = day_data['date']
            day_comments = ScheduleComment.objects.filter(
                group=student.group,
                is_active=True
            ).filter(
                Q(date=day_date) |
                Q(week_type=day_data['week_type'], day=day_date.isoweekday(), date__isnull=True)
            )
            day_data['has_comments'] = day_comments.exists()
            day_data['urgent_comments'] = day_comments.filter(is_urgent=True).exists()
            day_data['comments_count'] = day_comments.count()
        
        context = {
            'student': student,
            'group': student.group,
            'today': today,
            'tomorrow': tomorrow,
            'current_week_type': current_week_type,
            'current_week_display': current_week_display,
            'next_week_type': next_week_type,
            'next_week_display': next_week_display,
            'today_schedule': today_schedule,
            'tomorrow_schedule': tomorrow_schedule,
            'current_week_schedule': current_week_schedule,
            'next_week_schedule': next_week_schedule,
            'comments': comments,
            'today_comments': today_comments,
            'tomorrow_comments': tomorrow_comments,
            'month_days': month_days,
            'monday': today - timedelta(days=today.weekday()),
            'has_urgent': comments.filter(is_urgent=True).exists(),
        }
        
        return render(request, 'students/schedule.html', context)
        
    except Student.DoesNotExist:
        return redirect('student_login')
    except Exception as e:
        print(f"Ошибка в student_schedule: {e}")
        return redirect('student_dashboard')

# ==================== ПОСЕЩАЕМОСТЬ ====================

def student_attendance(request):
    """История пропусков с реальными данными"""
    student_id = request.session.get('student_id')
    if not student_id:
        return redirect('student_login')
    
    try:
        student = Student.objects.get(id=student_id)
        profile = StudentProfile.objects.get_or_create(user=student)[0]
        
        # Получаем реальные пропуски
        attendance_history = Attendance.objects.filter(student=student).order_by('-date')
        
        # Статистика по месяцам
        total_hours = attendance_history.aggregate(total=Sum('hours'))['total'] or 0
        remaining = max(0, 20 - total_hours)
        
        # Группировка по месяцам для графика
        months = {}
        for att in attendance_history:
            month_key = att.date.strftime('%Y-%m')
            if month_key not in months:
                months[month_key] = 0
            months[month_key] += att.hours
        
        context = {
            'student': student,
            'profile': profile,
            'history': attendance_history,
            'total_hours': total_hours,
            'remaining': remaining,
            'progress': min(100, (total_hours / 20) * 100),
            'months': months,
        }
        
        return render(request, 'students/attendance.html', context)
    except Student.DoesNotExist:
        return redirect('student_login')

# ==================== ПРИОРИТЕТЫ ====================

def student_priority(request):
    """Анализ приоритетов на основе реальных данных"""
    student_id = request.session.get('student_id')
    if not student_id:
        return redirect('student_login')
    
    try:
        student = Student.objects.get(id=student_id)
        
        # Получаем все предметы группы
        subjects = Subject.objects.filter(group=student.group)
        
        # Анализ по каждому предмету
        subject_analysis = []
        low_grades = []
        
        for subject in subjects:
            # Получаем успеваемость по предмету
            performance, created = StudentPerformance.objects.get_or_create(
                student=student,
                subject=subject,
                defaults={'total_points': 0}
            )
            
            # Получаем оценки по предмету
            grades = StudentGrade.objects.filter(student=student, subject=subject).order_by('-date')
            
            # Проверяем, есть ли проблемы
            is_problem = performance.total_points < 15
            grades_list = [g.raw_value for g in grades]
            
            if is_problem:
                low_grades.append({
                    'subject': subject.name,
                    'total': performance.total_points,
                    'remaining': performance.remaining_points,
                    'grades': ', '.join(grades_list) if grades_list else '—'
                })
            
            subject_analysis.append({
                'name': subject.name,
                'total': performance.total_points,
                'target': performance.target_points,
                'progress': performance.progress_percentage,
                'remaining': performance.remaining_points,
                'status': performance.status,
                'grades_count': grades.count(),
            })
        
        # Статистика пропусков
        attendances = Attendance.objects.filter(student=student)
        total_hours = attendances.aggregate(total=Sum('hours'))['total'] or 0
        
        # Генерируем рекомендации
        recommendations = []
        
        if low_grades:
            recommendations.append({
                'text': 'Уделите больше внимания предметам с низкими баллами',
                'type': 'danger',
                'subjects': [item['subject'] for item in low_grades]
            })
        
        if total_hours >= 15:
            recommendations.append({
                'text': f'Критический остаток пропусков! Осталось всего {20 - total_hours} часов',
                'type': 'danger'
            })
        elif total_hours >= 10:
            recommendations.append({
                'text': f'Осталось {20 - total_hours} часов пропусков. Старайтесь не пропускать',
                'type': 'warning'
            })
        else:
            recommendations.append({
                'text': 'Отличная посещаемость! Продолжайте в том же духе',
                'type': 'success'
            })
        
        # Рекомендации по предметам
        for subject in subject_analysis:
            if subject['status'] == 'danger':
                recommendations.append({
                    'text': f'Предмет "{subject["name"]}" требует внимания: {subject["total"]}/{subject["target"]} баллов',
                    'type': 'danger'
                })
            elif subject['status'] == 'warning' and subject['remaining'] <= 6:
                recommendations.append({
                    'text': f'До цели по предмету "{subject["name"]}" осталось {subject["remaining"]} баллов',
                    'type': 'warning'
                })
        
        context = {
            'student': student,
            'subject_analysis': subject_analysis,
            'low_grades': low_grades,
            'total_hours': total_hours,
            'grades_count': StudentGrade.objects.filter(student=student).count(),
            'recommendations': recommendations,
            'subjects_count': len(subjects),
        }
        
        return render(request, 'students/priority.html', context)
        
    except Student.DoesNotExist:
        return redirect('student_login')

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ КАЛЕНДАРЯ ====================

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
        week_type = get_week_type(date)
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

# ==================== API (опционально) ====================

@csrf_exempt
def api_get_grades(request):
    """API для получения оценок"""
    student_id = request.session.get('student_id')
    if not student_id:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        grades = StudentGrade.objects.filter(
            student_id=student_id
        ).select_related('subject').values(
            'id', 'subject__name', 'raw_value', 'points', 'date', 'comment'
        )
        return JsonResponse(list(grades), safe=False)
    except:
        return JsonResponse({'error': 'Error loading grades'}, status=500)

@csrf_exempt
def api_get_schedule(request):
    """API для получения расписания"""
    student_id = request.session.get('student_id')
    if not student_id:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        student = Student.objects.get(id=student_id)
        week_type = request.GET.get('week_type', get_week_type())
        
        schedule = Schedule.objects.filter(
            group=student.group,
            week_type__in=[week_type, 'both']
        ).order_by('day', 'pair_number').values(
            'id', 'day', 'pair_number', 'start_time', 'end_time',
            'subject', 'teacher', 'room', 'lesson_type'
        )
        
        return JsonResponse(list(schedule), safe=False)
    except:
        return JsonResponse({'error': 'Error loading schedule'}, status=500)