from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'Tildes — администрирование'

urlpatterns = [
    # Стандартная Django-админка. Адрес /admin занят админ-панелью сайта (frontend/src/panel)
    path('django-admin/', admin.site.urls),
    path('api/', include('learning.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
