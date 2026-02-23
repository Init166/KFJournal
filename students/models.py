from django.db import models
from admin_panel.models import Student, Group

class StudentProfile(models.Model):
    """Профиль студента"""
    user = models.OneToOneField('admin_panel.Student', on_delete=models.CASCADE, 
                                related_name='profile')
    group = models.ForeignKey('admin_panel.Group', on_delete=models.SET_NULL, 
                             null=True, related_name='student_profiles')
    
    # Данные из телеграм-бота
    total_hours = models.IntegerField(default=0, verbose_name="Всего пропусков")
    remaining_hours = models.IntegerField(default=20, verbose_name="Осталось часов")
    
    class Meta:
        verbose_name = "Профиль студента"
        verbose_name_plural = "Профили студентов"
    
    def __str__(self):
        return f"Профиль: {self.user.full_name}"

class Subject(models.Model):
    """Предметы (для автоматического заполнения в оценках)"""
    name = models.CharField(max_length=200, verbose_name="Название предмета")
    group = models.ForeignKey('admin_panel.Group', on_delete=models.CASCADE, 
                             related_name='subjects', null=True, blank=True)
    teacher = models.CharField(max_length=200, verbose_name="Преподаватель", blank=True)
    is_active = models.BooleanField(default=True, verbose_name="Активный")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Предмет"
        verbose_name_plural = "Предметы"
        ordering = ['name']
        unique_together = ['name', 'group']  # Предмет уникален в рамках группы
    
    def __str__(self):
        return f"{self.name} ({self.group.name})"

class Schedule(models.Model):
    """Расписание занятий"""
    WEEK_TYPES = [
        ('even', 'Чётная'),
        ('odd', 'Нечётная'),
        ('both', 'Обе'),
    ]
    
    DAYS_OF_WEEK = [
        (1, 'Понедельник'),
        (2, 'Вторник'),
        (3, 'Среда'),
        (4, 'Четверг'),
        (5, 'Пятница'),
        (6, 'Суббота'),
        (7, 'Воскресенье'),
    ]
    
    group = models.ForeignKey('admin_panel.Group', on_delete=models.CASCADE, 
                             related_name='schedules', verbose_name="Группа")
    day = models.IntegerField(choices=DAYS_OF_WEEK, verbose_name="День недели")
    week_type = models.CharField(max_length=4, choices=WEEK_TYPES, verbose_name="Тип недели")
    pair_number = models.IntegerField(verbose_name="Номер пары")
    start_time = models.CharField(max_length=10, verbose_name="Время начала", default="9:40")
    end_time = models.CharField(max_length=10, verbose_name="Время окончания", default="11:10")
    subject = models.CharField(max_length=200, verbose_name="Предмет")
    teacher = models.CharField(max_length=200, verbose_name="Преподаватель", blank=True)
    room = models.CharField(max_length=100, verbose_name="Аудитория", blank=True)
    lesson_type = models.CharField(max_length=50, verbose_name="Тип занятия", 
                                  choices=[('lecture', 'Лекция'), ('seminar', 'Семинар'), 
                                           ('practice', 'Практика'), ('lab', 'Лабораторная')],
                                  default='lecture')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Занятие"
        verbose_name_plural = "Расписание"
        ordering = ['day', 'pair_number']
        unique_together = ['group', 'day', 'week_type', 'pair_number']
    
    def __str__(self):
        day_name = dict(self.DAYS_OF_WEEK)[self.day]
        week_name = dict(self.WEEK_TYPES)[self.week_type]
        return f"{day_name} ({week_name}) - {self.pair_number} пара: {self.subject}"
    
    def save(self, *args, **kwargs):
        # При сохранении предмета, добавляем его в список предметов группы
        super().save(*args, **kwargs)
        Subject.objects.get_or_create(
            name=self.subject,
            group=self.group,
            defaults={'teacher': self.teacher}
        )

class ScheduleComment(models.Model):
    """Комментарии к расписанию"""
    group = models.ForeignKey('admin_panel.Group', on_delete=models.CASCADE, related_name='schedule_comments', verbose_name="Группа")
    comment = models.TextField(verbose_name="Комментарий")
    week_type = models.CharField(max_length=4, choices=Schedule.WEEK_TYPES, null=True, blank=True, verbose_name="Тип недели")
    day = models.IntegerField(choices=Schedule.DAYS_OF_WEEK, null=True, blank=True, verbose_name="День недели")
    lesson = models.ForeignKey('Schedule', on_delete=models.CASCADE, null=True, blank=True, related_name='comments', verbose_name="Занятие")
    date = models.DateField(null=True, blank=True, verbose_name="Конкретная дата")    
    is_urgent = models.BooleanField(default=False, verbose_name="Срочное")
    is_active = models.BooleanField(default=True, verbose_name="Активно")
    created_by = models.ForeignKey('admin_panel.Student', on_delete=models.SET_NULL, null=True, related_name='created_comments', verbose_name="Автор")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    class Meta:
        verbose_name = "Комментарий к расписанию"
        verbose_name_plural = "Комментарии к расписанию"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Комментарий: {self.comment[:50]}"

class StudentPerformance(models.Model):
    """Успеваемость студента по предметам"""
    student = models.ForeignKey('admin_panel.Student', on_delete=models.CASCADE,
                               related_name='performance')
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE,
                               related_name='student_performance')
    total_points = models.FloatField(default=0, verbose_name="Всего баллов")
    target_points = models.IntegerField(default=21, verbose_name="Цель")
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Успеваемость"
        verbose_name_plural = "Успеваемость"
        unique_together = ['student', 'subject']
    
    def __str__(self):
        return f"{self.student.full_name} - {self.subject.name}: {self.total_points}/{self.target_points}"
    
    @property
    def progress_percentage(self):
        """Возвращает процент прогресса"""
        if self.target_points:
            return min(100, (self.total_points / self.target_points) * 100)
        return 0
    
    @property
    def remaining_points(self):
        """Возвращает оставшиеся баллы до цели"""
        return max(0, self.target_points - self.total_points)
    
    @property
    def status(self):
        """Возвращает статус успеваемости"""
        if self.total_points >= self.target_points:
            return 'success'
        elif self.progress_percentage >= 70:
            return 'warning'
        else:
            return 'danger'


class GradeType(models.Model):
    """Типы оценок и их веса"""
    name = models.CharField(max_length=50, verbose_name="Название")
    display_name = models.CharField(max_length=100, verbose_name="Отображаемое название")
    points = models.FloatField(default=1, verbose_name="Баллы")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Тип оценки"
        verbose_name_plural = "Типы оценок"
    
    def __str__(self):
        return f"{self.display_name} ({self.points} балл)"



class StudentGrade(models.Model):
    """Оценки студента (расширенная версия)"""
    GRADE_TYPES = [
        ('performance', 'Выступление'),
        ('supplement', 'Дополнение'),
        ('question', 'Вопрос'),
        ('plus', '+'),
        ('minus', '-'),
        ('numeric_2', '2'),
        ('numeric_3', '3'),
        ('numeric_4', '4'),
        ('numeric_5', '5'),
        ('custom', 'Другое'),
    ]
    
    student = models.ForeignKey('admin_panel.Student', on_delete=models.CASCADE,
                               related_name='grades')
    group = models.ForeignKey('admin_panel.Group', on_delete=models.CASCADE,
                             related_name='grades', verbose_name="Группа")
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE,
                               related_name='grades')
    schedule = models.ForeignKey('Schedule', on_delete=models.SET_NULL,
                                null=True, blank=True, related_name='grades')
    
    # Тип оценки
    grade_type = models.CharField(max_length=20, choices=GRADE_TYPES, verbose_name="Тип оценки")
    raw_value = models.CharField(max_length=20, verbose_name="Исходное значение")
    points = models.FloatField(default=1, verbose_name="Баллы")
    
    # Метаданные
    date = models.DateField(verbose_name="Дата")
    is_today = models.BooleanField(default=False, verbose_name="Сегодняшняя дата")
    
    # Кто поставил
    marked_by = models.ForeignKey('admin_panel.Student', on_delete=models.SET_NULL,
                                 null=True, related_name='marked_grades')
    
    # Комментарий
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Оценка"
        verbose_name_plural = "Оценки"
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.student.full_name} - {self.subject.name}: {self.raw_value} ({self.points} баллов)"
    
    def save(self, *args, **kwargs):
        if not self.group_id:
            self.group = self.student.group
        self.calculate_points()
        super().save(*args, **kwargs)
    
    def calculate_points(self):
        points_map = {
            'performance': 1, 'supplement': 1, 'question': 1,
            'plus': 1, 'minus': 0,
            'numeric_2': 2, 'numeric_3': 3, 'numeric_4': 4, 'numeric_5': 5,
        }
        self.points = points_map.get(self.grade_type, 1)
    


class WeekType(models.Model):
    """Модель для хранения чётности недель"""
    date = models.DateField(unique=True, verbose_name="Дата")
    week_type = models.CharField(max_length=4, choices=[('even', 'Чётная'), ('odd', 'Нечётная')], 
                                verbose_name="Тип недели")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Тип недели"
        verbose_name_plural = "Типы недель"
        ordering = ['date']
    
    def __str__(self):
        return f"{self.date.strftime('%d.%m.%Y')} - {self.get_week_type_display()}"



class Attendance(models.Model):
    """Пропуски студентов (привязаны к группе)"""
    student = models.ForeignKey('admin_panel.Student', on_delete=models.CASCADE,
                               related_name='attendances', verbose_name="Студент")
    group = models.ForeignKey('admin_panel.Group', on_delete=models.CASCADE,
                             related_name='attendances', verbose_name="Группа")
    date = models.DateField(verbose_name="Дата пропуска")
    hours = models.IntegerField(verbose_name="Количество часов", 
                               choices=[(1, '1 час'), (2, '2 часа'), (3, '3 часа'), 
                                        (4, '4 часа'), (5, '5 часов'), (6, '6 часов'),
                                        (7, '7 часов'), (8, '8 часов')])
    reason = models.TextField(verbose_name="Причина", blank=True)
    marked_by = models.ForeignKey('admin_panel.Student', on_delete=models.SET_NULL,
                                 null=True, related_name='marked_attendances', 
                                 verbose_name="Кто отметил")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Пропуск"
        verbose_name_plural = "Пропуски"
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.student.full_name} - {self.hours}ч ({self.date})"
    
    def save(self, *args, **kwargs):
        if not self.group_id:
            self.group = self.student.group
        super().save(*args, **kwargs)
        # Обновляем профиль студента
        profile = StudentProfile.objects.get_or_create(user=self.student)[0]
        total = Attendance.objects.filter(student=self.student).aggregate(total=models.Sum('hours'))['total'] or 0
        profile.total_hours = total
        profile.remaining_hours = max(0, 20 - total)
        profile.save()


class SeminarSlot(models.Model):
    """Слоты для выступлений на семинарах (привязаны к группе)"""
    schedule = models.ForeignKey('Schedule', on_delete=models.CASCADE, 
                               related_name='seminar_slots',
                               limit_choices_to={'lesson_type': 'seminar'})
    group = models.ForeignKey('admin_panel.Group', on_delete=models.CASCADE,
                             related_name='seminar_slots', verbose_name="Группа")
    slot_number = models.IntegerField(verbose_name="Номер слота", choices=[(1, 'Слот 1'), (2, 'Слот 2')])
    student = models.ForeignKey('admin_panel.Student', on_delete=models.SET_NULL,
                              null=True, blank=True, related_name='seminar_slots')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Слот семинара"
        verbose_name_plural = "Слоты семинаров"
        unique_together = ['schedule', 'slot_number']
        ordering = ['schedule__day', 'schedule__pair_number', 'slot_number']
    
    def __str__(self):
        status = f" - {self.student.full_name}" if self.student else " - свободно"
        return f"{self.schedule.subject} ({self.slot_number}){status}"
    
    def save(self, *args, **kwargs):
        if not self.group_id:
            self.group = self.schedule.group
        super().save(*args, **kwargs)

    @property
    def subject_id(self):
        """Получение ID предмета через расписание"""
        if self.schedule:
            try:
                subject = Subject.objects.get(
                    name=self.schedule.subject,
                    group=self.schedule.group
                )
                return subject.id
            except Subject.DoesNotExist:
                return None
        return None