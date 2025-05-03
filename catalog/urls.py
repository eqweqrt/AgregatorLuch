# catalog/urls.py

from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # Главная страница каталога (в рамках /catalog/)
    path('', views.catalog_selection_view, name='catalog_selection'),

    # URL для обновления количества/удаления в выборе (AJAX)
    path('selection/update/', views.update_selection_view, name='update_selection'),

    # URL для генерации DOCX (основной вариант)
    path('selection/generate-docx/', views.generate_commercial_offer_docx_view, name='generate_commercial_offer_docx'),

    # === НОВЫЕ URL ДЛЯ ДОПОЛНИТЕЛЬНЫХ ВАРИАНТОВ DOCX ===
    path('selection/generate-umed-docx/', views.generate_commercial_offer_umed_docx_view, name='generate_commercial_offer_umed_docx'),
    path('selection/generate-pos78-docx/', views.generate_commercial_offer_pos78_docx_view, name='generate_commercial_offer_pos78_docx'),
    # ==================================================

    # URL для журнала документов
    path('document-log/', views.document_log_view, name='document_log'),
]

# Обработка статических и медиа файлов в режиме отладки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)