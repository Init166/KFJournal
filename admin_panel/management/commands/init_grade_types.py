# management/commands/init_grade_types.py
from django.core.management.base import BaseCommand
from students.models import GradeType

class Command(BaseCommand):
    def handle(self, *args, **options):
        types = [
            {'name': 'performance', 'display_name': 'Выступление', 'points': 1},
            {'name': 'supplement', 'display_name': 'Дополнение', 'points': 1},
            {'name': 'question', 'display_name': 'Вопрос', 'points': 1},
            {'name': 'plus', 'display_name': '+', 'points': 1},
            {'name': 'minus', 'display_name': '-', 'points': 0},
        ]
        
        for t in types:
            GradeType.objects.get_or_create(
                name=t['name'],
                defaults=t
            )
        
        self.stdout.write(self.style.SUCCESS('✅ Типы оценок созданы'))