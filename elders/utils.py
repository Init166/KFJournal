from datetime import datetime, timedelta
from students.models import WeekType

def get_week_type_for_date(target_date):
    """
    Определяет тип недели для конкретной даты
    Сначала проверяет ручные настройки в БД, если нет - вычисляет автоматически
    """
    try:
        # Сначала ищем вручную заданные даты
        week_type = WeekType.objects.filter(date=target_date).first()
        if week_type:
            return week_type.week_type
    except:
        pass
    
    # Автоматический расчет (по вашему расписанию)
    # Берем первую известную дату из вашего списка
    known_dates = [
        (datetime(2026, 1, 5).date(), 'even'),   # 05.01.26 - чётная
        (datetime(2026, 1, 12).date(), 'odd'),   # 12.01.26 - нечётная
        (datetime(2026, 1, 19).date(), 'even'),  # 19.01.26 - чётная
        (datetime(2026, 1, 26).date(), 'odd'),   # 26.01.26 - нечётная
        (datetime(2026, 2, 2).date(), 'even'),   # 02.02.26 - чётная
        (datetime(2026, 2, 9).date(), 'odd'),    # 09.02.26 - нечётная
        (datetime(2026, 2, 16).date(), 'even'),  # 16.02.26 - чётная
        (datetime(2026, 2, 23).date(), 'odd'),   # 23.02.26 - нечётная
        (datetime(2026, 3, 2).date(), 'even'),   # 02.03.26 - чётная
        (datetime(2026, 3, 9).date(), 'odd'),    # 09.03.26 - нечётная
        (datetime(2026, 3, 16).date(), 'even'),  # 16.03.26 - чётная
        (datetime(2026, 3, 23).date(), 'odd'),   # 23.03.26 - нечётная
        (datetime(2026, 3, 30).date(), 'even'),  # 30.03.26 - чётная
        (datetime(2026, 4, 6).date(), 'odd'),    # 06.04.26 - нечётная
        (datetime(2026, 4, 13).date(), 'even'),  # 13.04.26 - чётная
        (datetime(2026, 4, 20).date(), 'odd'),   # 20.04.26 - нечётная
        (datetime(2026, 4, 27).date(), 'even'),  # 27.04.26 - чётная
        (datetime(2026, 5, 4).date(), 'odd'),    # 04.05.26 - нечётная
        (datetime(2026, 5, 11).date(), 'even'),  # 11.05.26 - чётная
        (datetime(2026, 5, 18).date(), 'odd'),   # 18.05.26 - нечётная
        (datetime(2026, 5, 25).date(), 'even'),  # 25.05.26 - чётная
        (datetime(2026, 6, 1).date(), 'odd'),    # 01.06.26 - нечётная
        (datetime(2026, 6, 8).date(), 'even'),   # 08.06.26 - чётная
        (datetime(2026, 6, 15).date(), 'odd'),   # 15.06.26 - нечётная
        (datetime(2026, 6, 22).date(), 'even'),  # 22.06.26 - чётная
        (datetime(2026, 6, 29).date(), 'odd'),   # 29.06.26 - нечётная
    ]
    
    # Находим ближайшую известную дату
    known_dates.sort(key=lambda x: x[0])
    
    for known_date, known_type in known_dates:
        if target_date >= known_date:
            days_diff = (target_date - known_date).days
            weeks_diff = days_diff // 7
            # Если прошло четное количество недель - тип сохраняется, если нечетное - меняется
            if weeks_diff % 2 == 0:
                return known_type
            else:
                return 'odd' if known_type == 'even' else 'even'
    
    # Если ничего не нашли, считаем от 01.01.2026
    start_date = datetime(2026, 1, 1).date()
    days_diff = (target_date - start_date).days
    weeks_diff = days_diff // 7
    return 'odd' if weeks_diff % 2 == 0 else 'even'

def get_current_week_type():
    """Возвращает тип текущей недели"""
    return get_week_type_for_date(datetime.now().date())