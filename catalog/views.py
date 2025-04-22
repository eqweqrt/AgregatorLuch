# catalog/views.py

import os
import datetime
import base64
from io import BytesIO
from pathlib import Path

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.conf import settings
from django.urls import reverse_lazy
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Max

# === Импорты для работы с DOCX (python-docx) ===
from docx import Document
from docx.shared import Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.shared import OxmlElement, qn
# === Конец импортов DOCX ===

# === Импорты для работы с PDF (xhtml2pdf) ===
from xhtml2pdf import pisa
from xhtml2pdf.files import pisaFileObject
# === Конец импортов PDF ===

# Импорт для Pillow (оционально, для определения MIME-типа изображений)
try:
    from PIL import Image
    PIL_INSTALLED = True
except ImportError:
    PIL_INSTALLED = False
    print("Warning: Pillow not installed. Image MIME type detection will be based on file extension only.")

# === Убедитесь, что эти импорты есть и правильные из .models: ===
from .models import Category, Product, ProductModel, DocumentLog, get_next_document_number
# =====================================================


# =============================================================================
# ПАТЧ ДЛЯ РЕШЕНИЯ ПРОБЛЕМЫ С TTF НА WINDOWS (issue #623 в xhtml2pdf)
# =============================================================================
print("Applying pisaFileObject patch for Windows TTF issue...")
try:
    original_getNamedFile = pisaFileObject.getNamedFile
    pisaFileObject.getNamedFile = lambda self: self.uri
    setattr(pisaFileObject, '_patched_for_windows_ttf', True)
    print("PisaFileObject patch applied successfully.")
except Exception as e:
    print(f"Error applying pisaFileObject patch: {e}")
# =============================================================================
# КОНЕЦ ПАТЧА
# =============================================================================


# Ваше пользовательское представление входа
class CustomLoginView(LoginView):
    template_name = 'registration/login.html'

    def get_redirect_url(self):
        redirect_to = super().get_redirect_url()
        if self.request.user.is_superuser:
            return reverse_lazy('admin:index')
        return redirect_to

# Ваше представление для домашней страницы
@login_required
def home_view(request):
    """Отображает домашнюю страницу после входа."""
    return render(request, 'home.html')


# --- Ваше объединенное представление для каталога и выбора ---
@login_required
def catalog_selection_view(request):
    """
    Отображает список всех моделей продуктов, сгруппированных по категориям и продуктам,
    и текущий выбор пользователя.
    """
    print("Executing catalog_selection_view...")
    product_models = ProductModel.objects.all().select_related('product__category', 'product').order_by('product__category__name', 'product__name', 'name')
    print(f"Query returned {product_models.count()} ProductModel objects.")

    structured_catalog = {}
    for model in product_models:
        if not hasattr(model, 'product') or model.product is None or not hasattr(model.product, 'category') or model.product.category is None:
             print(f"Warning: Model ID {model.id} does not have a linked product or category. Skipping.")
             continue
        category = model.product.category
        product = model.product
        if category not in structured_catalog:
            structured_catalog[category] = {}
        if product not in structured_catalog[category]:
            structured_catalog[category][product] = []
        structured_catalog[category][product].append(model)

    print(f"Structured catalog has {len(structured_catalog)} categories.")

    selection = request.session.get('selection', {})
    selected_items = []
    total_price = 0

    for model_id_str, quantity in list(selection.items()):
         try:
            model = ProductModel.objects.select_related('product').get(id=int(model_id_str))
            quantity = int(quantity) if quantity is not None else 0
            if quantity < 0: quantity = 0

            if quantity > 0:
                 item_total = model.price * quantity
                 selected_items.append({
                     'model': model, 'quantity': quantity, 'unit_price': model.price, 'item_total': item_total,
                 })
                 total_price += item_total
            elif model_id_str in selection:
                 print(f"Warning: Found zero or negative quantity ({quantity}) for model ID {model_id_str}. Removing from selection.")
                 del selection[model_id_str]
                 request.session.modified = True

         except (ProductModel.DoesNotExist, ValueError) as e:
             if model_id_str in selection:
                 print(f"Error processing selected item ID {model_id_str}: {e}. Removing from selection.")
                 del selection[model_id_str]
                 request.session.modified = True
                 messages.warning(request, f"Warning: Removed invalid model ID {model_id_str} from selection.")

         except Exception as e:
              print(f"An unexpected error occurred while processing selected item ID {model_id_str} for display: {e}")
              continue

    print(f"Selected items list for summary has {len(selected_items)} items.")

    context = {
        'structured_catalog': structured_catalog,
        'selection': selection,
        'selected_items': selected_items,
        'total_price': total_price,
    }
    print("Rendering catalog_selection.html...")
    return render(request, 'catalog/catalog_selection.html', context)


@require_POST
@login_required
def update_selection_view(request):
    """
    Обновляет количество выбранных моделей в сессии по AJAX запросу.
    """
    print(f"Executing AJAX update_selection_view for user {request.user.username}, data: {request.POST}")
    action = request.POST.get('action')

    if not action:
        print("Error: Missing action in POST request.")
        return HttpResponseBadRequest("Отсутствует действие.")

    if action == 'clear':
        request.session['selection'] = {}
        request.session.modified = True
        print("Action 'clear': Selection has been emptied.")
        return HttpResponse("OK: Selection cleared.", status=200)

    model_id_str = request.POST.get('model_id')
    if not model_id_str:
         print(f"Error: Missing model_id for action '{action}' in POST request.")
         return HttpResponseBadRequest(f"Отсутствует ID модели для действия '{action}'.")

    try:
        model_id = int(model_id_str)
        product_model = ProductModel.objects.select_related('product').get(id=model_id)
        print(f"Successfully retrieved ProductModel ID {model_id} ({product_model.name}).")

    except (ValueError, ProductModel.DoesNotExist) as e:
        error_message = f"Модель с ID {model_id_str} не найдена или некорректна: {e}"
        print(f"Error processing model ID {model_id_str}: {e}")
        selection_check = request.session.get('selection', {})
        if model_id_str in selection_check:
             del selection_check[model_id_str]
             request.session['selection'] = selection_check
             request.session.modified = True
             print(f"Removed invalid/non-existent model ID {model_id_str} from session.")
        status_code = 404 if isinstance(e, ProductModel.DoesNotExist) else 400
        return HttpResponse(error_message, status=status_code)
    except Exception as e:
         error_message = f"Неожиданная ошибка при получении модели ID {model_id_str}: {e}"
         print(error_message)
         return HttpResponse(error_message, status=500)

    selection = request.session.get('selection', {})
    print(f"Current selection before update: {selection}")

    if action == 'add':
        selection[model_id_str] = selection.get(model_id_str, 0) + 1
        print(f"Action 'add': Added 1. New quantity: {selection[model_id_str]}.")

    elif action == 'remove':
        if model_id_str in selection:
            selection[model_id_str] -= 1
            if selection[model_id_str] <= 0:
                del selection[model_id_str]
                print(f"Action 'remove': Removed 1. Quantity dropped to 0 or less, removed.")
            else:
                 print(f"Action 'remove': Removed 1. New quantity: {selection[model_id_str]}.")
        else:
             print("Action 'remove': Model not in selection.")

    elif action == 'remove_all':
        if model_id_str in selection:
            del selection[model_id_str]
            print(f"Action 'remove_all': Removed model ID {model_id_str} ({product_model.name}) completely.")
        else:
             print("Action 'remove_all': Model not in selection.")

    elif action == 'set':
        quantity_str = request.POST.get('quantity', '0')
        try:
            quantity = int(quantity_str)
            if quantity >= 0:
                if quantity > 0:
                    selection[model_id_str] = quantity
                    print(f"Action 'set': Quantity set to {quantity}.")
                elif quantity == 0:
                     if model_id_str in selection:
                        del selection[model_id_str]
                        print("Action 'set': Quantity set to 0, removed from selection.")
                     else:
                         print("Action 'set': Quantity set to 0 for model not in selection. No change.")
            else:
                print(f"Action 'set': Invalid quantity (negative): {quantity_str}.")
                return HttpResponseBadRequest("Количество должно быть неотрицательным числом.")

        except ValueError:
            print(f"Action 'set': Invalid quantity format: '{quantity_str}'.")
            return HttpResponseBadRequest(f"Некорректное значение количества: '{quantity_str}'. Должно быть целое число.")

    else:
        print(f"Error: Unknown action '{action}'.")
        return HttpResponseBadRequest(f"Неизвестное действие: '{action}'")

    request.session['selection'] = selection
    request.session.modified = True
    print(f"New selection saved to session: {request.session['selection']}")

    return HttpResponse("OK", status=200)


# --- Хелпер функции для PDF ---
def get_font_base64(font_path):
    """Читает файл шрифта по локальному пути и возвращает его содержимое в Base64."""
    try:
        with open(font_path, 'rb') as font_file:
            encoded_string = base64.b64encode(font_file.read()).decode('ascii')
            return encoded_string
    except FileNotFoundError:
        print(f"Error: Font file NOT FOUND at {font_path}")
        return None
    except Exception as e:
        print(f"Error encoding font file {font_path}: {e}")
        return None

def get_image_base64(image_path):
    """Reads an image file by its local path and returns its Base64 Data URI (for PDF)."""
    global PIL_INSTALLED
    try:
        with open(image_path, 'rb') as image_file:
            if PIL_INSTALLED:
                try:
                    img = Image.open(image_file)
                    mime_type = Image.MIME.get(img.format, 'image/png')
                    image_file.seek(0)
                except Exception as pil_e:
                     print(f"Warning: Pillow failed to identify image format for {image_path}: {pil_e}. Falling back to extension.")
                     PIL_INSTALLED = False
                finally:
                     if not PIL_INSTALLED or 'mime_type' not in locals():
                        extension = os.path.splitext(image_path)[1].lower()
                        if extension == '.png': mime_type = 'image/png'
                        elif extension in ['.jpg', '.jpeg']: mime_type = 'image/jpeg'
                        elif extension == '.gif': mime_type = 'image/gif'
                        else:
                             print(f"Warning: Unknown image extension '{extension}' for {image_path}. Defaulting to image/png.")
                             mime_type = 'image/png'
            else:
                extension = os.path.splitext(image_path)[1].lower()
                if extension == '.png': mime_type = 'image/png'
                elif extension in ['.jpg', '.jpeg']: mime_type = 'image/jpeg'
                elif extension == '.gif': mime_type = 'image/gif'
                else:
                     print(f"Warning: Unknown image extension '{extension}' for {image_path} and Pillow not installed. Defaulting to image/png.")
                     mime_type = 'image/png'

            encoded_string = base64.b64encode(image_file.read()).decode('ascii')
            data_uri = f'data:{mime_type};base64,{encoded_string}'
            return data_uri
    except FileNotFoundError:
        print(f"Error: Image file NOT FOUND at {image_path}")
        return None
    except Exception as e:
        print(f"Error encoding image file {image_path}: {e}")
        return None


# --- Представление для генерации PDF ---
@login_required
def generate_commercial_offer_pdf_view(request):
    """
    Генерирует PDF коммерческого предложения с выбранными моделями,
    их описаниями (details) и изображениями.
    """
    print("\nEntering generate_commercial_offer_pdf_view...")

    selection = request.session.get('selection', {})
    selected_items_data = []
    total_price = 0

    if not selection:
        messages.info(request, "Ваш выбор пуст. Невозможно сформировать PDF.")
        print("Selection is empty, redirecting.")
        return redirect('catalog_selection')

    # --- Сбор данных о выбранных товарах ---
    for model_id_str, quantity in list(selection.items()):
         try:
            model = ProductModel.objects.select_related('product').get(id=int(model_id_str))
            quantity = int(quantity) if quantity is not None else 0

            if quantity > 0:
                 image_data_uri = None
                 if model.image and hasattr(model.image, 'path') and os.path.exists(model.image.path):
                      image_path = model.image.path
                      image_data_uri = get_image_base64(image_path)
                 elif model.image:
                      print(f"Warning: Image file for Model ID {model.id} ({model.image.name}) not found on disk at {getattr(model.image, 'path', 'N/A')}")

                 item_total = model.price * quantity
                 selected_items_data.append({
                     'model': model, 'quantity': quantity, 'unit_price': model.price,
                     'item_total': item_total, 'image_data_uri': image_data_uri,
                 })
                 total_price += item_total
            elif model_id_str in selection:
                 print(f"Warning: Found zero or negative quantity ({quantity}) for model ID {model_id_str} during PDF generation. Removing from selection.")
                 del selection[model_id_str]
                 request.session.modified = True

         except (ProductModel.DoesNotExist, ValueError) as e:
             if model_id_str in selection:
                 print(f"Error processing model ID {model_id_str} for PDF: {e}. Removing from selection.")
                 del selection[model_id_str]
                 request.session.modified = True
                 messages.warning(request, f"Одна из выбранных позиций (ID: {model_id_str}) не найдена.")
             continue
         except Exception as e:
              print(f"An unexpected error occurred while processing model ID {model_id_str} for PDF: {e}")
              messages.error(request, f"Произошла неожиданная ошибка при обработке позиции (ID: {model_id_str}): {e}")
              continue

    if not selected_items_data:
         messages.warning(request, "В вашем выборе нет корректных позиций для формирования PDF.")
         print("selected_items_data is empty after processing, redirecting.")
         return redirect('catalog_selection')

    # === Логируем создание документа ===
    document_number = None
    try:
        document_number = get_next_document_number()
        log_entry = DocumentLog(user=request.user, document_number=document_number, document_type='pdf')
        log_entry.save()
        print(f"Logged PDF generation: Number={document_number}, User={request.user.username}")
    except Exception as e:
        print(f"Error logging PDF generation: {e}")
        messages.error(request, f"Ошибка при записи в журнал документов: {e}. Документ может быть сгенерирован без номера.")

    # === Определяем строковые представления даты и номера документа ===
    doc_date_str = datetime.date.today().strftime('%d.%m.%Y')
    doc_number_str = str(document_number) if document_number is not None else ""

    # --- Получение локальных путей к файлам шрифтов DejaVu Sans ---
    font_dir_path = settings.BASE_DIR / 'static' / 'fonts'
    print(f"Checking font directory: {font_dir_path}")

    dejavu_sans_regular_path = font_dir_path / 'DejaVuSans.ttf'
    dejavu_sans_bold_path = font_dir_path / 'DejaVuSans-Bold.ttf'

    dejavu_sans_regular_base64 = get_font_base64(str(dejavu_sans_regular_path))
    dejavu_sans_bold_base64 = get_font_base64(str(dejavu_sans_bold_path))

    if not dejavu_sans_regular_base64 or not dejavu_sans_bold_base64:
        error_msg = "Не удалось загрузить необходимые шрифты DejaVu Sans для PDF. Проверьте файлы шрифтов в static/fonts."
        print(error_msg)
        messages.error(request, error_msg)
        return redirect('catalog_selection')

    context = {
        'selected_items': selected_items_data, 'total_price': total_price, 'offer_title': 'Коммерческое предложение',
        'delivery_terms': '20 рабочих дней', 'warranty_terms': '12 месяцев',
        'manager_name': 'Логинов Алексей', 'company_name': 'ЛУЧ-IT (ООО «Луч АйТи)',
        'manager_contact': '+7-382-299-56-13', 'manager_email': 'komdir@luch-it.ru',
        'manager_signature_name': 'Логинов А. А.', 'attorney_details': 'Доверенность от 01.02.2024г',
        'document_date': datetime.date.today(), 'document_number': document_number,
        'dejavu_sans_regular_base64': dejavu_sans_regular_base64,
        'dejavu_sans_bold_base64': dejavu_sans_bold_base64,
    }
    print("Context prepared for PDF template.")

    html_string = render_to_string('catalog/commercial_offer_pdf_template.html', context)

    result = BytesIO()
    print("Calling pisa.CreatePDF...")
    try:
        pisa_status = pisa.CreatePDF(
           html_string.encode('utf-8'), dest=result, encoding='utf-8',
        )
        print("pisa.CreatePDF call finished.")
    except Exception as e:
        print(f"\n{'='*50}\nPISA CreatePDF threw an exception: {e}\n{'='*50}\n")
        messages.error(request, f"Критическая ошибка при вызове pisa.CreatePDF: {e}. Проверьте логи сервера.")
        return redirect('catalog_selection')

    if pisa_status.err:
        print("\n" + "="*50)
        print("PISA Error during PDF generation (pisa_status.err is True):")
        if isinstance(pisa_status.err, list):
             for i, err in enumerate(pisa_status.err):
                 print(f"Error {i+1}: {err}")
                 if hasattr(err, 'msg'): print(f"  Message: {err.msg}")
                 if hasattr(err, 'url'): print(f"  URL: {err.url}")
        else:
             print(f"Single Error: {pisa_status.err}")
             if hasattr(pisa_status.err, 'msg'): print(f"  Message: {pisa_status.err.msg}")
             if hasattr(pisa_status.err, 'url'): print(f"  URL: {pisa_status.err.url}")
        print("="*50 + "\n")
        messages.error(request, "Произошла ошибка при генерации PDF файла. Проверьте логи сервера.")
        return redirect('catalog_selection')

    pdf_bytes = result.getvalue()
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    filename = f"commercial_offer_{doc_number_str or 'undated'}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    print("PDF generated successfully. Returning HttpResponse.")
    return response


# === Хелпер функция для добавления границ к ячейке DOCX ===
def set_cell_border(cell, **kwargs):
    """Применяет границы к ячейке Word."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()

    borders = {
        'top': {'val': 'single', 'sz': 12, 'color': '#000000'},
        'bottom': {'val': 'single', 'sz': 12, 'color': '#000000'},
        'left': {'val': 'single', 'sz': 12, 'color': '#000000'},
        'right': {'val': 'single', 'sz': 12, 'color': '#000000'},
    }

    for border_name, border_props in kwargs.items():
        if border_name in borders:
             borders[border_name] = border_props
        elif border_name in ['top', 'bottom', 'left', 'right'] and border_props is None:
             borders[border_name] = None

    tcBorders = tcPr.first_child_found_in('w:tcBorders')
    if tcBorders is None:
        tcBorders = OxmlElement('w:tcBorders')
        tcPr.append(tcBorders)

    for border_name, border_props in borders.items():
        border_element = tcBorders.find(qn('w:' + border_name))
        if border_props is not None:
            if border_element is None:
                border_element = OxmlElement('w:' + border_name)
                tcBorders.append(border_element)
            for key, value in border_props.items():
                 border_element.set(qn('w:' + key), str(value))
        else:
            if border_element is not None:
                 tcBorders.remove(border_element)


# --- Универсальная функция для генерации DOCX ---
def generate_docx_offer(request, template_file_name, filename_prefix):
    """
    Генерирует DOCX коммерческого предложения по указанному шаблону.
    """
    print(f"\nEntering generate_docx_offer with template: {template_file_name}")

    # --- Сбор данных о выбранных товарах ---
    selection = request.session.get('selection', {})
    selected_items_data = []
    total_price = 0

    if not selection:
        messages.info(request, "Ваш выбор пуст. Невозможно сформировать DOCX.")
        print("Selection is empty, redirecting.")
        return redirect('catalog_selection')

    print("Starting to collect selected items data...")
    for model_id_str, quantity in list(selection.items()):
         try:
            model = ProductModel.objects.select_related('product').get(id=int(model_id_str))
            quantity = int(quantity) if quantity is not None else 0

            if quantity > 0:
                image_path = None
                if model.image and hasattr(model.image, 'path') and os.path.exists(model.image.path):
                     image_path = model.image.path
                elif model.image:
                     print(f"Warning: Image file for Model ID {model.id} ({model.image.name}) not found on disk at {getattr(model.image, 'path', 'N/A')}")

                item_total = model.price * quantity
                # === ДОБАВЛЕНО ДЛЯ ОТЛАДКИ ===
                print(f"DEBUG: Item {model.name} (ID: {model.id}) - Price: {model.price}, Quantity: {quantity}, Calculated item_total: {item_total}")
                # ==============================
                selected_items_data.append({
                    'model': model, 'quantity': quantity, 'unit_price': model.price,
                    'item_total': item_total, 'image_path': image_path,
                })
                total_price += item_total
            elif model_id_str in selection:
                 print(f"Warning: Found zero or negative quantity ({quantity}) for model ID {model_id_str} during DOCX generation. Removing from selection.")
                 del selection[model_id_str]
                 request.session.modified = True

         except (ProductModel.DoesNotExist, ValueError) as e:
             if model_id_str in selection:
                 print(f"Error processing model ID {model_id_str} for DOCX: {e}. Removing from selection.")
                 del selection[model_id_str]
                 request.session.modified = True
                 messages.warning(request, f"Одна из выбранных позиций (ID: {model_id_str}) не найдена или некорректна и была удалена.")
             continue
         except Exception as e:
              print(f"An unexpected error occurred while processing model ID {model_id_str} for DOCX: {e}")
              messages.error(request, f"Произошла неожиданная ошибка при обработке позиции (ID: {model_id_str}): {e}")
              continue

    if not selected_items_data:
         messages.warning(request, "В вашем выборе нет корректных позиций для формирования DOCX.")
         print("selected_items_data is empty after processing, redirecting.")
         return redirect('catalog_selection')

    # === Логируем создание документа ===
    document_number = None
    try:
        document_number = get_next_document_number()
        log_entry = DocumentLog(
            user=request.user,
            document_number=document_number,
            document_type='docx'
        )
        log_entry.save()
        print(f"Logged DOCX document generation: Number={document_number}, User={request.user.username}, Template={template_file_name}")
    except Exception as e:
        print(f"Error logging DOCX generation: {e}")
        messages.error(request, f"Ошибка при записи в журнал документов: {e}. Документ может быть сгенерирован без номера.")

    # === Определяем строковые представления даты и номера документа ===
    doc_date_str = datetime.date.today().strftime('%d.%m.%Y')
    doc_number_str = str(document_number) if document_number is not None else ""

    # === Определяем путь к шаблонному файлу DOCX ===
    template_path = settings.BASE_DIR / 'templates' / template_file_name
    print(f"Attempting to load DOCX template from: {template_path}")

    if not template_path.exists():
        error_msg = f"Критическая ошибка: Шаблонный файл DOCX не найден по пути {template_path}. Невозможно сгенерировать документ без шаблона."
        print(error_msg)
        messages.error(request, error_msg + f" Убедитесь, что файл '{template_file_name}' существует в папке templates вашего проекта.")
        return redirect('catalog_selection')

    try:
        document = Document(template_path)
        print(f"Successfully loaded DOCX template from {template_path}")
    except Exception as e:
        error_msg = f"Ошибка при загрузке шаблонного DOCX файла из {template_path}: {e}"
        print(error_msg)
        messages.error(request, error_msg)
        return redirect('catalog_selection')

    # --- Замена текстовых плейсхолдеров ---
    placeholders = {
        '{{document_date}}': doc_date_str,
        '{{document_number}}': doc_number_str if doc_number_str else 'б/н',
    }

    def simple_replace_placeholders_in_paragraphs(paragraphs_list):
        for paragraph in paragraphs_list:
            paragraph_text = paragraph.text
            replaced_text = paragraph_text
            for key, value in placeholders.items():
                if key in replaced_text:
                    replaced_text = replaced_text.replace(key, str(value))
            if replaced_text != paragraph_text:
                 paragraph.clear()
                 paragraph.add_run(replaced_text)

    simple_replace_placeholders_in_paragraphs(document.paragraphs)
    for section in document.sections:
         if section.header: simple_replace_placeholders_in_paragraphs(section.header.paragraphs)
         if section.footer: simple_replace_placeholders_in_paragraphs(section.footer.paragraphs)
    for tbl in document.tables:
        for row in tbl.rows:
            for cell in row.cells:
                simple_replace_placeholders_in_paragraphs(cell.paragraphs)
    print("Placeholder replacement finished.")


    # --- Вставка таблицы товаров (ищем плейсхолдер) ---
    table_placeholder_text = '[PRODUCT_TABLE]'
    table_placeholder_paragraph = None
    for p in document.paragraphs:
        if table_placeholder_text in p.text:
            table_placeholder_paragraph = p
            break

    if not table_placeholder_paragraph:
        error_msg = f"Ошибка: В шаблонном файле DOCX '{template_file_name}' не найден маркер '{table_placeholder_text}'. Убедитесь, что он присутствует в шаблоне в основном теле документа."
        print(error_msg)
        messages.error(request, error_msg)
        print("Skipping table insertion because placeholder was not found.")
        output = BytesIO()
        try:
            document.save(output)
            output.seek(0)
            response = HttpResponse(output.getvalue(),
                                    content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            filename = f"commercial_offer_{filename_prefix}_{doc_number_str or 'undated'}_no_table.docx"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            print("DOCX generated successfully (No table - placeholder missing). Returning HttpResponse.")
            return response
        except Exception as e:
            save_error_msg = f"Ошибка при сохранении DOCX файла без таблицы ('{template_file_name}'): {e}."
            print(save_error_msg)
            messages.error(request, save_error_msg)
            return HttpResponse("Error saving DOCX file without table: " + str(e), status=500)


    # === Определяем точку вставки таблицы и удаляем плейсхолдер ===
    parent_element = table_placeholder_paragraph._element.getparent()
    placeholder_index = parent_element.index(table_placeholder_paragraph._element)
    parent_element.remove(table_placeholder_paragraph._element)


    # === Создаем НОВУЮ таблицу и вставляем ее на место плейсхолдера ===
    print("Creating table with 1 row for headers...")
    table = document.add_table(rows=1, cols=4) # 4 колонки: Товар, Кол-во, Цена, Сумма

    # Вставляем таблицу на место удаленного абзаца-плейсхолдера
    table_element = table._element
    body = document._body._element
    # Ищем последний элемент <w:tbl> в теле документа
    last_table_element_in_body = body.xpath('.//w:tbl')[-1] if body.xpath('.//w:tbl') else None

    if last_table_element_in_body is not None and last_table_element_in_body == table_element:
        # Если новая таблица оказалась в конце (как она обычно добавляется), удаляем ее оттуда
        try:
             body.remove(last_table_element_in_body)
             print("Removed newly added table from end of body.")
        except ValueError:
             # Это может произойти, если таблица уже была перемещена
             print("Warning: Could not remove newly added table from end of body (it might have already been moved).")

    # Вставляем таблицу на правильное место
    try:
        parent_element.insert(placeholder_index, table_element)
        print(f"Inserted table element at index {placeholder_index}.")
    except Exception as insert_e:
        print(f"Error inserting table element at placeholder index {placeholder_index}: {insert_e}. It might remain at the end.")
        # Если вставка не удалась, таблица, вероятно, осталась в конце


    # --- Заполнение таблицы ---
    # Заголовки таблицы (заполняем первую строку, созданную при init)
    print("Filling table headers...")
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Товар'
    hdr_cells[1].text = 'Кол-во, шт.'
    hdr_cells[2].text = 'Цена за ед., руб.'
    hdr_cells[3].text = 'Сумма, руб.'
    for cell in hdr_cells:
        if cell.paragraphs:
            paragraph = cell.paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                 run.bold = True
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


    # Заполнение строк таблицы данными (используем add_row() для каждого элемента)
    print(f"Adding {len(selected_items_data)} rows for items...")
    for i, item in enumerate(selected_items_data):
       print(f"  Adding row for item {i+1}/{len(selected_items_data)}: {item['model'].name}")
       # === Добавляем новую строку для каждого элемента ===
       row_cells = table.add_row().cells # Каждая новая ячейка содержит один пустой абзац.

       # === Заполнение первой ячейки (Наименование / Описание / Изображение) ===
       product_info_cell = row_cells[0]
       # Исправленная логика: Очищаем все существующие абзацы, затем добавляем новые
       # Важно: Итерируем по копии списка, чтобы избежать проблем при удалении элементов во время итерации
       for p in list(product_info_cell.paragraphs):
            p._element.getparent().remove(p._element)

       # 1. Абзац для изображения (если есть)
       if item['image_path'] and os.path.exists(item['image_path']):
           try:
               p_image = product_info_cell.add_paragraph()
               run = p_image.add_run()
               image_width_cm = 4.0
               run.add_picture(str(item['image_path']), width=Cm(image_width_cm))
               p_image.alignment = WD_ALIGN_PARAGRAPH.CENTER
               p_image.paragraph_format.space_after = Cm(0.1)
           except Exception as e:
               print(f"    Error adding image {item['image_path']} to DOCX table cell: {e}")
               img_name = getattr(item['model'].image, 'name', 'имя файла неизвестно') if item['model'].image else 'файл изображения не прикреплен'
               p_error = product_info_cell.add_paragraph()
               p_error.add_run(f"[Ошибка загрузки изображения: {img_name}]").italic = True
               p_error.paragraph_format.space_after = Cm(0.1)
       elif item['model'].image:
            img_name = getattr(item['model'].image, 'name', 'имя файла неизвестно')
            p_warning = product_info_cell.add_paragraph()
            p_warning.add_run(f"[Изображение модели '{item['model'].name}' не найдено на диске: {img_name}]").runs[-1].italic = True
            p_warning.paragraph_format.space_after = Cm(0.1)


       # 2. Абзац для Названия Модели
       p_name = product_info_cell.add_paragraph()
       p_name.add_run(f"{item['model'].product.name} - {item['model'].name}").bold = True
       p_name.paragraph_format.space_after = Cm(0.1)

       # 3. Абзацы для Описания Модели
       if item['model'].details:
           details_text = item['model'].details
           for j, line in enumerate(details_text.splitlines()):
                line = line.strip()
                if line:
                     p_details = product_info_cell.add_paragraph()
                     p_details.add_run(line).italic = True
                     p_details.paragraph_format.space_before = Cm(0.05)
                     p_details.paragraph_format.space_after = Cm(0.05)

       # Вертикальное выравнивание для ячейки
       product_info_cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP

       # === Конец заполнения первой ячейки ===


       # Заполнение остальных ячеек в этой строке (Кол-во, Цена, Сумма)
       # Используем .text для установки текста, а затем форматируем первый абзац.
       # Это более простой и, возможно, более надежный способ для этих ячеек.

       qty_cell = row_cells[1]
       qty_cell.text = str(item['quantity'])
       if qty_cell.paragraphs:
            qty_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
       qty_cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

       price_cell = row_cells[2]
       price_cell.text = f"{item['unit_price']:.2f}"
       if price_cell.paragraphs:
            price_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
       price_cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

       total_cell = row_cells[3]
       total_cell.text = f"{item['item_total']:.2f}"
       if total_cell.paragraphs:
            # Делаем текст суммы жирным
            for run in total_cell.paragraphs[0].runs:
                 run.bold = True
            total_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
       total_cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


    # Строка Итого (добавляем новую строку)
    print("Adding total row...")
    total_row = table.add_row()
    total_row_cells = total_row.cells

    # Объединяем ячейки (первые три)
    merged_total_cell = total_row_cells[0].merge(total_row_cells[1]).merge(total_row_cells[2])

    # === ИСПРАВЛЕННАЯ ЛОГИКА: ЗАПОЛНЕНИЕ ОБЪЕДИНЕННОЙ ЯЧЕЙКИ ДЛЯ "ИТОГО:" ===
    # Устанавливаем текст напрямую, это создаст/заменит первый абзац.
    merged_total_cell.text = "Итого:"
    # Затем форматируем первый абзац.
    if merged_total_cell.paragraphs:
        paragraph = merged_total_cell.paragraphs[0]
        for run in paragraph.runs: # Делаем весь текст в абзаце жирным
             run.bold = True
        paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT # Выравнивание по правому краю
    # Вертикальное выравнивание ячейки
    merged_total_cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


    # Заполняем последнюю ячейку (4-ю) в строке Итого общей суммой
    final_total_cell = total_row_cells[3]

    # === ДОБАВЛЕНО ДЛЯ ОТЛАДКИ ===
    print(f"DEBUG: Calculated total_price before insertion into DOCX: {total_price}, type: {type(total_price)}")
    # ==============================

    # === ИСПРАВЛЕННАЯ ЛОГИКА: ЗАПОЛНЕНИЕ ЯЧЕЙКИ С СУММОЙ ИТОГО ===
    # Устанавливаем текст напрямую, это создаст/заменит первый абзац.
    final_total_cell.text = f"{total_price:.2f}"
    # Затем форматируем первый абзац.
    if final_total_cell.paragraphs:
        paragraph = final_total_cell.paragraphs[0]
        for run in paragraph.runs: # Делаем весь текст в абзаце жирным
            run.bold = True
        paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT # Выравнивание по правому краю
    # Вертикальное выравнивание ячейки
    final_total_cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


    # === Применяем границы ко всем ячейкам таблицы программно ===
    print("Applying borders to table cells programmatically...")
    try:
        for row in table.rows:
            for cell in row.cells:
                set_cell_border(cell)
        print("Programmatic borders applied.")
    except Exception as e:
        print(f"Error applying programmatic borders: {e}")
        messages.warning(request, f"Не удалось применить границы к таблице программно: {e}. Убедитесь, что библиотека python-docx установлена корректно и имеет необходимые компоненты.")
        print(f"If borders are missing, ensure they are set in the template file: {template_path}")
        messages.info(request, "Если границы таблицы не появились, настройте их в шаблонном файле DOCX через Microsoft Word.")


    # --- Сохранение и возврат HttpResponse ---
    print("Saving modified DOCX to BytesIO...")
    output = BytesIO()
    try:
        document.save(output)
        output.seek(0)
        print(f"Generated DOCX bytes length: {len(output.getvalue())} bytes.")
    except Exception as e:
         error_msg = f"Ошибка при сохранении DOCX файла ('{template_file_name}'): {e}."
         print(error_msg)
         messages.error(request, error_msg)
         return HttpResponse("Error saving DOCX file: " + str(e), status=500)

    filename = f"commercial_offer_{filename_prefix}_{doc_number_str or 'undated'}.docx"
    response = HttpResponse(output.getvalue(),
                            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    print("DOCX generated successfully. Returning HttpResponse.")
    return response


# --- Представления-обертки для универсальной функции ---

@login_required
def generate_commercial_offer_docx_view(request):
    """Генерирует основной вариант DOCX КП."""
    return generate_docx_offer(request, 'commercial_offer_template.docx', 'main')

@login_required
def generate_commercial_offer_umed_docx_view(request):
    """Генерирует DOCX КП для Учебного мира."""
    return generate_docx_offer(request, 'commercial_offer_umed_template.docx', 'umed')

@login_required
def generate_commercial_offer_pos78_docx_view(request):
    """Генерирует DOCX КП для ПОС78."""
    return generate_docx_offer(request, 'commercial_offer_pos78_template.docx', 'pos78')


@user_passes_test(lambda u: u.is_staff)
@login_required
def document_log_view(request):
    """Отображает список всех созданных записей DocumentLog для администраторов."""
    print(f"Executing document_log_view for user {request.user.username}")
    logs = DocumentLog.objects.all().order_by('-timestamp')
    context = {'logs': logs}
    print(f"Found {logs.count()} document log entries. Rendering document_log.html...")
    return render(request, 'catalog/document_log.html', context)