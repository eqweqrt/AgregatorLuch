from django.contrib import admin
# Импортируем все нужные модели, включая DocumentLog
from .models import Category, Product, ProductModel, DocumentLog

# Регистрируем существующие модели (убедитесь, что они уже есть и не закомментированы)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(ProductModel)

# === Регистрация модели DocumentLog для админ-панели ===

@admin.register(DocumentLog) # Используем декоратор для регистрации
class DocumentLogAdmin(admin.ModelAdmin):
    """
    Настройки отображения модели DocumentLog в админ-панели.
    """
    # Поля, которые будут отображаться в списке записей журнала
    list_display = ('document_number', 'user', 'timestamp', 'document_type')

    # Добавляем фильтры на боковую панель (для удобства поиска)
    list_filter = ('document_type', 'timestamp', 'user')

    # Добавляем возможность поиска по указанным полям
    search_fields = ('document_number__iexact', 'user__username__icontains', 'document_type') # __iexact для точного номера (без учета регистра), __icontains для поиска по части имени пользователя

    # Делаем все поля только для чтения в детальном представлении (нельзя изменить запись журнала после создания)
    readonly_fields = ('document_number', 'user', 'timestamp', 'document_type')

    # Сортировка записей по умолчанию (по убыванию времени создания)
    ordering = ('-timestamp',)

# === Конец регистрации DocumentLog ===

# Убедитесь, что у вас нет других admin.site.register(DocumentLog) ниже,
# если вы использовали декоратор @admin.register.