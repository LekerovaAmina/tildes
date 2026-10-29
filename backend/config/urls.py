from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'Tildes — администрирование'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('learning.urls')),
]
