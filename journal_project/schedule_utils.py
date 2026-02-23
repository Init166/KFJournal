# schedule_utils.py
from datetime import datetime

def get_week_type(target_date=None):
    """
    Определяет тип недели (чётная/нечётная) для указанной даты.
    Возвращает "even" для чётной, "odd" для нечётной недели.
    """
    if target_date is None:
        target_date = datetime.today().date()
    
    # Начальная точка отсчета - первая неделя сентября (нечётная)
    start_date = datetime(2024, 9, 2).date()  # Первый понедельник сентября
    
    # Вычисляем разницу в неделях
    delta = target_date - start_date
    weeks_passed = delta.days // 7
    
    # Если прошло четное количество недель - нечётная, нечетное - чётная
    return "even" if weeks_passed % 2 == 1 else "odd"

def get_russian_day_name(english_day_name):
    """
    Получить русское название дня недели
    """
    days_mapping = {
        'monday': 'Понедельник',
        'tuesday': 'Вторник',
        'wednesday': 'Среда', 
        'thursday': 'Четверг',
        'friday': 'Пятница',
        'saturday': 'Суббота',
        'sunday': 'Воскресенье'
    }
    return days_mapping.get(english_day_name.lower(), english_day_name)