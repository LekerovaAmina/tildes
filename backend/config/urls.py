from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

admin.site.site_header = 'Tildes — администрирование'

urlpatterns = [
    # Стандартная Django-админка. Адрес /admin занят админ-панелью сайта (frontend/src/panel)
    path('django-admin/', admin.site.urls),
    # Документация API: схема OpenAPI и Swagger UI (до include, чтобы не перехватили маршруты learning)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/', include('learning.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
