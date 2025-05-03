from django.contrib import admin
from django.urls import path, include # include остался
from django.views.generic import RedirectView # <-- Импортируем RedirectView
from django.contrib.auth import views as auth_views
from catalog import views
from catalog.views import CustomLoginView # Убедитесь, что CustomLoginView импортирован, если используется для логина

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', RedirectView.as_view(pattern_name='catalog_selection', permanent=False), name='index_redirect'),
    path('catalog/', include('catalog.urls')),
    path('upload-file/', views.upload_file, name='upload_file'),
    path('file-list/', views.file_list, name='file_list'),
    path('download-file/<int:file_id>/', views.download_file, name='download_file'),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)