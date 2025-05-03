from django.contrib import admin
from .models import Category, Product, ProductModel, DocumentLog
from .models import File

# Регистрация существующих моделей
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(ProductModel)

# === Регистрация модели DocumentLog ===
@admin.register(DocumentLog)
class DocumentLogAdmin(admin.ModelAdmin):
    list_display = ('document_number', 'user', 'timestamp', 'document_type', 'file_link')
    list_filter = ('document_type', 'timestamp', 'user')
    search_fields = ('document_number__iexact', 'user__username__icontains', 'document_type')
    readonly_fields = ('document_number', 'user', 'timestamp', 'document_type')
    ordering = ('-timestamp',)

    def file_link(self, obj):
        if obj.file:
            return f'<a href="{obj.file.url}" target="_blank">Скачать</a>'
        return "Файл отсутствует"

    file_link.allow_tags = True
    file_link.short_description = "Файл"

@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    """
    Настройки отображения модели File в админ-панели.
    """
    list_display = ('name', 'uploaded_by', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at', 'uploaded_by')
    search_fields = ('name__icontains', 'uploaded_by__username__icontains')
    readonly_fields = ('uploaded_by', 'created_at')
    ordering = ('-created_at',)

    def save_model(self, request, obj, form, change):
        """
        Автоматически присваиваем пользователя, который загрузил файл.
        """
        if not obj.uploaded_by_id:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)