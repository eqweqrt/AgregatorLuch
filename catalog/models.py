from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models import Max

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название категории")
    description = models.TextField(blank=True, null=True, verbose_name="Описание категории")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name="Категория")
    name = models.CharField(max_length=100, verbose_name="Название продукта")
    # Оставляем description здесь, если продукт сам по себе может иметь описание
    description = models.TextField(blank=True, null=True, verbose_name="Описание продукта")

    class Meta:
        unique_together = ('category', 'name')
        ordering = ['category__name', 'name']
        verbose_name = "Продукт"
        verbose_name_plural = "Продукты"

    def __str__(self):
        return f"{self.category.name} - {self.name}"

class ProductModel(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='models', verbose_name="Продукт")
    name = models.CharField(max_length=100, verbose_name="Название модели")
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Цена модели продукта",
        verbose_name="Цена"
    )
    # Используем поле details для хранения описания модели, как выяснилось
    details = models.TextField(blank=True, null=True, verbose_name="Описание модели") # Переименовал verbose_name для ясности

    # === ДОБАВЛЯЕМ ПОЛЕ ДЛЯ ИЗОБРАЖЕНИЯ ===
    image = models.ImageField(
        upload_to='product_models/', # Папка внутри MEDIA_ROOT
        blank=True, # Поле не является обязательным
        null=True,  # Разрешает NULL в базе данных
        verbose_name="Изображение модели"
    )
    # =====================================
    # Если вы ДОБАВЛЯЛИ поле description сюда и хотите использовать ЕГО,
    # раскомментируйте строку ниже и используйте 'description' вместо 'details'
    # во вьюхе и шаблоне.
    # description = models.TextField(verbose_name="Уникальное описание модели", blank=True, null=True)


    class Meta:
        unique_together = ('product', 'name')
        ordering = ['product__name', 'name']
        verbose_name = "Модель продукта"
        verbose_name_plural = "Модели продуктов"


    def __str__(self):
        # Отображение в админке и т.д.
        return f"{self.product.name} - {self.name} (ID: {self.id}, Цена: {self.price})"

class DocumentLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Пользователь"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата и время создания"
    )
    document_number = models.PositiveIntegerField(
        verbose_name="Номер документа",
        unique=True,
        help_text="Автоматически генерируемый номер документа"
    )
    document_type = models.CharField(
        max_length=10,
        choices=[('pdf', 'PDF'), ('docx', 'DOCX')],
        verbose_name="Тип документа"
    )
    # Новое поле для хранения файла
    file = models.FileField(
        upload_to='documents/',
        blank=True,
        null=True,
        verbose_name="Файл документа"
    )

    def __str__(self):
        user_info = self.user.username if self.user else "Неизвестный пользователь"
        return f"Документ №{self.document_number} ({self.document_type}) от {self.timestamp.strftime('%d.%m.%Y %H:%M')} создан пользователем {user_info}"

    class Meta:
        verbose_name = "Журнал документа"
        verbose_name_plural = "Журнал документов"
        ordering = ['-timestamp']

# Вспомогательная функция для получения следующего номера документа
def get_next_document_number():
    """Определяет следующий доступный номер документа."""
    # Находим максимальный номер документа в текущем журнале
    last_log = DocumentLog.objects.aggregate(max_num=Max('document_number'))
    # Если записей нет, начинаем с 1, иначе увеличиваем максимальный номер на 1
    next_number = (last_log['max_num'] or 0) + 1
    return next_number

class File(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название файла")
    file = models.FileField(upload_to='files/', verbose_name="Файл")
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_files', verbose_name="Загружен админом")
    is_active = models.BooleanField(default=True, verbose_name="Доступен для скачивания")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Файл"
        verbose_name_plural = "Файлы"