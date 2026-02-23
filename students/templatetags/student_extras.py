# students/templatetags/student_extras.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Получение значения из словаря по ключу"""
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def multiply(value, arg):
    """Умножает значение на аргумент"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """Делит значение на аргумент"""
    try:
        if float(arg) == 0:
            return 0
        return (float(value) / float(arg)) * 100
    except (ValueError, TypeError):
        return 0

@register.filter
def grade_color(value):
    """Возвращает класс цвета для оценки"""
    try:
        points = float(value)
        if points >= 4.5:
            return 'success'
        elif points >= 3.5:
            return 'primary'
        elif points >= 2.5:
            return 'warning'
        else:
            return 'danger'
    except:
        return 'secondary'

@register.filter
def week_type_name(week_type):
    """Возвращает название типа недели"""
    if week_type == 'even':
        return 'Чётная'
    elif week_type == 'odd':
        return 'Нечётная'
    return week_type