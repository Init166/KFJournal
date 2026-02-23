# journal_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf.urls import handler404
from django.views.generic.base import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from core.views import custom_404_view

urlpatterns = [
    path('admin-panel/', include('admin_panel.urls')),  # НАША кастомная админка - ДОЛЖНА БЫТЬ ПЕРВОЙ
    path('admin/', admin.site.urls),                    # Стандартная админка Django - ПОСЛЕ нашей
    path('students/', include('students.urls')),
    path('elders/', include('elders.urls')),
    path('', include('core.urls')),
]

# Отключаем favicon ошибку (перенаправляем на наш логотип)
urlpatterns += [
    path('favicon.ico', RedirectView.as_view(url='/static/images/logo.svg', permanent=True)),
]

# Настраиваем обработчик 404 ошибок
handler404 = custom_404_view

# Для обслуживания медиафайлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)