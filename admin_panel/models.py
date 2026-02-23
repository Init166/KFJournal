from django.db import models
from django.contrib.auth.models import User

# ==================== ОБРАЗОВАТЕЛЬНЫЕ СТРУКТУРЫ ====================

class EducationalLevel(models.Model):
    """Уровень образования (Бакалавриат, Магистратура, Специалитет)"""
    name = models.CharField(max_length=100, verbose_name="Название")
    order = models.IntegerField(default=0, verbose_name="Порядок сортировки")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Уровень образования"
        verbose_name_plural = "Уровни образования"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
    
    def student_count(self):
        count = 0
        for form in self.forms.all():
            for course in form.courses.all():
                for group in course.groups.all():
                    count += group.students.count()
        return count


class StudyForm(models.Model):
    """Форма обучения (Очная, Заочная, Очно-заочная)"""
    name = models.CharField(max_length=100, verbose_name="Название")
    level = models.ForeignKey('EducationalLevel', on_delete=models.CASCADE, 
                             related_name='forms', verbose_name="Уровень образования")
    order = models.IntegerField(default=0, verbose_name="Порядок сортировки")
    
    class Meta:
        verbose_name = "Форма обучения"
        verbose_name_plural = "Формы обучения"
        ordering = ['order', 'name']
    
    def __str__(self):
        return f"{self.level.name} - {self.name}"
    
    def student_count(self):
        count = 0
        for course in self.courses.all():
            for group in course.groups.all():
                count += group.students.count()
        return count


class Course(models.Model):
    """Курс (1, 2, 3, 4)"""
    number = models.IntegerField(verbose_name="Номер курса")
    form = models.ForeignKey('StudyForm', on_delete=models.CASCADE, 
                           related_name='courses', verbose_name="Форма обучения")
    order = models.IntegerField(default=0, verbose_name="Порядок сортировки")
    
    class Meta:
        verbose_name = "Курс"
        verbose_name_plural = "Курсы"
        ordering = ['number']
    
    def __str__(self):
        return f"{self.number} курс"
    
    def student_count(self):
        return sum(group.students.count() for group in self.groups.all())


class Group(models.Model):
    """Учебная группа"""
    name = models.CharField(max_length=50, verbose_name="Название группы")
    course = models.ForeignKey('Course', on_delete=models.CASCADE, 
                             related_name='groups', verbose_name="Курс")
    form = models.ForeignKey('StudyForm', on_delete=models.CASCADE, 
                           related_name='groups', verbose_name="Форма обучения")
    level = models.ForeignKey('EducationalLevel', on_delete=models.CASCADE, 
                            related_name='groups', verbose_name="Уровень образования")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Группа"
        verbose_name_plural = "Группы"
        ordering = ['name']
    
    def __str__(self):
        return self.name


# ==================== ПОЛЬЗОВАТЕЛИ ====================

class Student(models.Model):
    """Пользователь (студент, староста, деканат, отдел, преподаватель)"""
    USER_TYPES = [
        ('student', '🎓 Студент'),
        ('elder', '⭐ Староста'),
        ('dean', '🏛️ Деканат'),
        ('department', '📋 Отдел'),
        ('teacher', '👨‍🏫 Преподаватель'),
        ('admin', '🛠️ Администратор'),
    ]
    
    login = models.CharField(max_length=100, unique=True, verbose_name="Логин")
    password = models.CharField(max_length=128, default='', verbose_name="Пароль")
    full_name = models.CharField(max_length=200, verbose_name="ФИО")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Телефон")
    group = models.ForeignKey('Group', on_delete=models.SET_NULL, 
                            null=True, blank=True, related_name='students', 
                            verbose_name="Группа")
    user_type = models.CharField(max_length=20, choices=USER_TYPES, 
                               default='student', verbose_name="Тип пользователя")
    is_elder = models.BooleanField(default=False, verbose_name="Староста")
    is_active = models.BooleanField(default=True, verbose_name="Активный")
    telegram_id = models.BigIntegerField(null=True, blank=True, verbose_name="Telegram ID")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ['full_name']
    
    def __str__(self):
        return f"{self.full_name} ({self.get_user_type_display()})"
    
    def save(self, *args, **kwargs):
        if not self.password:
            import random
            import string
            chars = string.ascii_letters + string.digits
            self.password = ''.join(random.choice(chars) for _ in range(8))
        super().save(*args, **kwargs)


# ==================== ПРАВА И РАЗРЕШЕНИЯ ====================

class ElderPermission(models.Model):
    """Расширенные права для старост"""
    PERMISSION_TYPES = [
        ('add_students', '➕ Добавление студентов'),
        ('edit_students', '✏️ Редактирование студентов'),
        ('delete_students', '🗑️ Удаление студентов'),
        ('manage_schedule', '📅 Управление расписанием'),
        ('manage_attendance', '✅ Учет посещаемости'),
        ('manage_grades', '📊 Управление оценками'),
        ('create_chat', '💬 Создание чатов'),
        ('export_reports', '📄 Экспорт отчетов'),
    ]
    
    # ВАЖНО: используем строку 'Student', а не Student
    student = models.OneToOneField('Student', on_delete=models.CASCADE, 
                                  related_name='permissions', verbose_name="Староста")
    permissions = models.JSONField(default=dict, verbose_name="Права")
    can_manage_elders = models.BooleanField(default=False, verbose_name="Управление старостами")
    max_students = models.IntegerField(default=100, verbose_name="Макс. студентов")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Права старосты"
        verbose_name_plural = "Права старост"
    
    def __str__(self):
        return f"Права: {self.student.full_name}"


# ==================== ОТДЕЛЫ И СОТРУДНИКИ ====================

class Department(models.Model):
    """Отдел/Деканат/Подразделение"""
    DEPARTMENT_TYPES = [
        ('deanery', '🏛️ Деканат'),
        ('teacher', '👨‍🏫 Преподаватель'),
        ('administration', '📋 Администрация'),
        ('other', '🔧 Другое'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="Название")
    department_type = models.CharField(max_length=20, choices=DEPARTMENT_TYPES, 
                                      default='other', verbose_name="Тип")
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, 
                              null=True, blank=True, related_name='children',
                              verbose_name="Родительский отдел")
    order = models.IntegerField(default=0, verbose_name="Порядок сортировки")
    
    class Meta:
        verbose_name = "Отдел"
        verbose_name_plural = "Отделы"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class Employee(models.Model):
    """Сотрудник ВУЗа"""
    POSITION_TYPES = [
        ('teacher', '👨‍🏫 Преподаватель'),
        ('dean', '🏛️ Декан'),
        ('deputy_dean', '📋 Зам. декана'),
        ('methodist', '📊 Методист'),
        ('admin', '🛠️ Администратор'),
        ('other', '🔧 Другое'),
    ]
    
    login = models.CharField(max_length=100, unique=True, verbose_name="Логин")
    full_name = models.CharField(max_length=200, verbose_name="ФИО")
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Телефон")
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, 
                                 null=True, related_name='employees',
                                 verbose_name="Отдел")
    position = models.CharField(max_length=50, choices=POSITION_TYPES, 
                              default='other', verbose_name="Должность")
    is_active = models.BooleanField(default=True, verbose_name="Активный")
    telegram_id = models.BigIntegerField(null=True, blank=True, verbose_name="Telegram ID")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"
        ordering = ['full_name']
    
    def __str__(self):
        return f"{self.full_name} - {self.get_position_display()}"


# ==================== ЛОГИРОВАНИЕ ====================

class DatabaseLog(models.Model):
    """Логи действий с базами данных"""
    ACTION_TYPES = [
        ('create', '✅ Создание'),
        ('update', '✏️ Редактирование'),
        ('delete', '🗑️ Удаление'),
        ('move', '🔄 Перемещение'),
        ('import', '📎 Импорт'),
        ('export', '📤 Экспорт'),
    ]
    
    # ИСПРАВЛЕНИЕ: делаем поле более гибким - храним только ID и тип пользователя
    user_id = models.IntegerField(null=True, blank=True, verbose_name="ID пользователя")
    user_type = models.CharField(max_length=20, null=True, blank=True, verbose_name="Тип пользователя")
    user_name = models.CharField(max_length=200, null=True, blank=True, verbose_name="Имя пользователя")
    
    action = models.CharField(max_length=20, choices=ACTION_TYPES, verbose_name="Действие")
    model_name = models.CharField(max_length=100, verbose_name="Модель")
    object_id = models.IntegerField(null=True, blank=True, verbose_name="ID объекта")
    details = models.JSONField(default=dict, verbose_name="Детали")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP адрес")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Лог"
        verbose_name_plural = "Логи"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.model_name} - {self.created_at}"

class NavigationHistory(models.Model):
    """История навигации для кнопок Назад/Вперёд"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    content_type = models.CharField(max_length=50, verbose_name="Тип контента")
    object_id = models.IntegerField(verbose_name="ID объекта")
    title = models.CharField(max_length=200, verbose_name="Название")
    path = models.CharField(max_length=500, verbose_name="Путь")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "История навигации"
        verbose_name_plural = "История навигации"
        ordering = ['-created_at']


class ActionCache(models.Model):
    """Кэш действий для отмены (как корзина)"""
    ACTION_TYPES = [
        ('delete', '🗑️ Удаление'),
        ('edit', '✏️ Редактирование'),
        ('move', '🔄 Перемещение'),
        ('create', '✅ Создание'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    action = models.CharField(max_length=20, choices=ACTION_TYPES, verbose_name="Действие")
    model_name = models.CharField(max_length=100, verbose_name="Модель")
    object_id = models.IntegerField(null=True, blank=True, verbose_name="ID объекта")
    object_data = models.JSONField(default=dict, verbose_name="Данные объекта")
    parent_data = models.JSONField(default=dict, verbose_name="Данные родителя")
    created_at = models.DateTimeField(auto_now_add=True)
    is_restored = models.BooleanField(default=False, verbose_name="Восстановлено")
    
    class Meta:
        verbose_name = "Кэш действия"
        verbose_name_plural = "Кэш действий"
        ordering = ['-created_at']

class DeletedItemCache(models.Model):
    """Корзина удаленных элементов"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Кто удалил")
    item_type = models.CharField(max_length=50, verbose_name="Тип элемента")
    item_id = models.IntegerField(verbose_name="ID элемента")
    item_data = models.JSONField(verbose_name="Данные элемента")
    parent_data = models.JSONField(default=dict, verbose_name="Данные родителя")
    deleted_at = models.DateTimeField(auto_now_add=True, verbose_name="Время удаления")
    expires_at = models.DateTimeField(verbose_name="Истекает")
    is_restored = models.BooleanField(default=False, verbose_name="Восстановлено")
    
    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзина"
        ordering = ['-deleted_at']
    
    def __str__(self):
        return f"{self.item_type} #{self.item_id} удален {self.deleted_at}"


class ActionHistory(models.Model):
    """История действий для кнопок Назад/Вперёд"""
    ACTION_TYPES = [
        ('create', '✅ Создание'),
        ('update', '✏️ Редактирование'),
        ('delete', '🗑️ Удаление'),
        ('move', '🔄 Перемещение'),
    ]
    
    user_id = models.IntegerField(verbose_name="ID пользователя")
    user_name = models.CharField(max_length=200, verbose_name="Имя пользователя")
    action = models.CharField(max_length=20, choices=ACTION_TYPES, verbose_name="Действие")
    model_name = models.CharField(max_length=100, verbose_name="Модель")
    object_id = models.IntegerField(verbose_name="ID объекта")
    object_data = models.JSONField(verbose_name="Данные до/после")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "История действий"
        verbose_name_plural = "История действий"
        ordering = ['-created_at']