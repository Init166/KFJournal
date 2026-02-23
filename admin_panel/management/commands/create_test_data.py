# admin_panel/management/commands/create_test_data.py
from django.core.management.base import BaseCommand
from admin_panel.models import EducationalLevel, StudyForm, Course, Group, Student, Department, Employee
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Создание тестовых данных для админ-панели'
    
    def handle(self, *args, **kwargs):
        # Создаем уровни образования
        bachelor = EducationalLevel.objects.create(name='Бакалавриат', order=1)
        master = EducationalLevel.objects.create(name='Магистратура', order=2)
        specialist = EducationalLevel.objects.create(name='Специалитет', order=3)
        
        # Создаем формы обучения
        fulltime = StudyForm.objects.create(name='Очная форма', level=bachelor, order=1)
        extramural = StudyForm.objects.create(name='Заочная форма', level=bachelor, order=2)
        
        # Создаем курсы
        course1 = Course.objects.create(number=1, form=fulltime, order=1)
        course2 = Course.objects.create(number=2, form=fulltime, order=2)
        course3 = Course.objects.create(number=3, form=fulltime, order=3)
        
        # Создаем группы
        group103 = Group.objects.create(
            name='СПД-103', 
            course=course1,
            form=fulltime,
            level=bachelor
        )
        
        # Создаем отделы
        deanery = Department.objects.create(
            name='Деканат юридического факультета',
            department_type='deanery'
        )
        
        subdepartment = Department.objects.create(
            name='Кафедра теории государства и права',
            department_type='teacher',
            parent=deanery
        )
        
        self.stdout.write(self.style.SUCCESS('✅ Тестовые данные созданы!'))