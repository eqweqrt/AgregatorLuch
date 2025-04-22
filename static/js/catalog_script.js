// static/js/catalog_script.js

document.addEventListener('DOMContentLoaded', function() {

    // --- Логика сворачивания/разворачивания (без изменений) ---
    const toggleElements = document.querySelectorAll('.category-item > .toggle-icon, .category-item > .toggle-text.category-name, .product-item > .toggle-icon, .product-item > .toggle-text.product-name');

    toggleElements.forEach(toggleElement => {
        toggleElement.addEventListener('click', function() {
            const isCategoryToggle = this.classList.contains('category-name') || (this.classList.contains('toggle-icon') && this.closest('.category-item'));
            const isProductToggle = this.classList.contains('product-name') || (this.classList.contains('toggle-icon') && this.closest('.product-item'));

            let parentItem = null;
            let collapsibleContent = null;
            let toggleIcon = null;

            if (isCategoryToggle) {
                 parentItem = this.closest('.category-item');
                 collapsibleContent = parentItem ? parentItem.querySelector('.category-content.collapsible') : null;
                 toggleIcon = parentItem ? parentItem.querySelector('.category-item > .toggle-icon') : null;
            } else if (isProductToggle) {
                 parentItem = this.closest('.product-item');
                 collapsibleContent = parentItem ? parentItem.querySelector('.product-content.collapsible') : null;
                 toggleIcon = parentItem ? parentItem.querySelector('.product-item > .toggle-icon') : null;
            }

            if (collapsibleContent && toggleIcon) {
                 collapsibleContent.classList.toggle('collapsed');
                 toggleIcon.classList.toggle('expanded');
            } else {
                 console.warn("Не найдены элементы для сворачивания внутри:", parentItem || this);
            }
        });
    });
    // --- Конец логики сворачивания ---


    // --- AJAX Логика для обновления выбора ---

    // Функция для получения CSRF токена из куки (без изменений)
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    const csrftoken = getCookie('csrftoken'); // Получаем CSRF токен при загрузке страницы

    // === ИЗМЕНЕНО: Используем переменные из шаблона ===
    // Проверяем, что переменные определены (на случай, если скрипт загрузился без шаблона)
    const updateUrl = typeof UPDATE_SELECTION_URL !== 'undefined' ? UPDATE_SELECTION_URL : '/catalog/selection/update/'; // Fallback URL
    const catalogUrl = typeof CATALOG_SELECTION_URL !== 'undefined' ? CATALOG_SELECTION_URL : '/catalog/'; // Fallback URL для GET запроса

    if (typeof UPDATE_SELECTION_URL === 'undefined' || typeof CATALOG_SELECTION_URL === 'undefined') {
         console.error("JavaScript variables UPDATE_SELECTION_URL or CATALOG_SELECTION_URL are not defined! Ensure script block in template is correct.");
    }
    // ============================================

    // Именованная функция для обработчика клика AJAX кнопки (без изменений, кроме использования updateUrl)
    function handleAjaxButtonClick(event) {
         const button = this;
         event.preventDefault();
         if (button.classList.contains('disabled')) { return; }
         const action = button.dataset.action;
         let modelId = button.dataset.modelId;
         let quantity = null;

         if (action === 'set') {
             const form = button.closest('form');
             if (!form) { console.error("Кнопка 'set' не найдена внутри формы."); return; }
             const modelIdInput = form.querySelector('input[name="model_id"]');
             if (modelIdInput) { modelId = modelIdInput.value; }
             const quantityInput = form.querySelector('input[name="quantity"]');
             if (quantityInput) { quantity = quantityInput.value; }
         }

         if (!modelId && action !== 'clear') { console.error(`Ошибка: Не удалось получить model_id для действия '${action}'.`); return; }

         if (action === 'clear') {
             if (!confirm('Вы уверены, что хотите очистить весь выбор?')) {
                 return;
             }
         }


         const formData = new FormData();
         formData.append('action', action);
         if (modelId !== null) { formData.append('model_id', modelId); }
         if (quantity !== null) { formData.append('quantity', quantity); }

         const headers = {
              'X-CSRFToken': csrftoken,
              'X-Requested-With': 'XMLHttpRequest',
         };

         // === ИСПОЛЬЗУЕМ ПЕРЕДАННЫЙ URL ===
         fetch(updateUrl, {
             method: 'POST',
             headers: headers,
             body: formData,
         })
         .then(response => {
             if (!response.ok) {
                 return response.text().then(text => {
                      throw new Error(`HTTP error ${response.status}: ${text || response.statusText}`);
                 });
             }
             return response.text(); // Ожидаем текст "OK" или что-то подобное
         })
         .then(data => {
             console.log('AJAX update successful:', data);
             // После успешного обновления на сервере, обновляем UI
             updateSummaryBlock(); // Вызываем функцию обновления summary
         })
         .catch(error => {
             console.error('AJAX update failed:', error);
             alert('Произошла ошибка при обновлении выбора: ' + error.message);
         });
    }

     // Функция для обновления только summary блока (и прикрепления слушателей)
     // Используем catalogUrl для GET запроса
    function updateSummaryBlock() {
         const summaryContainer = document.querySelector('.selection-summary-content');
         if (summaryContainer) {
             // === ИСПОЛЬЗУЕМ ПЕРЕДАННЫЙ URL ===
             fetch(catalogUrl)
                .then(response => {
                     if (!response.ok) {
                         return response.text().then(text => {
                             throw new Error(`HTTP error ${response.status}: ${text || response.statusText}`);
                         });
                     }
                     return response.text();
                })
                .then(html => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const newSummaryContent = doc.querySelector('.selection-summary-content');
                    if (newSummaryContent) {
                        summaryContainer.innerHTML = newSummaryContent.innerHTML;
                        attachSummaryButtonListeners(); // ПОВЕСИТЬ СЛУШАТЕЛИ НА НОВЫЕ КНОПКИ В SUMMARY
                        updateDocumentButtonState(); // Обновить состояние кнопок генерации документов/очистки
                        // TODO: Возможно, обновить количество в input[type="number"] в каталоге?
                        // Для этого нужно получить selection из нового HTML, или чтобы update_selection_view возвращала JSON.
                        // Пока оставляем так.
                    } else {
                       console.error("Не удалось найти блок .selection-summary-content в ответе GET запроса при обновлении summary.");
                    }
                })
                .catch(error => {
                     console.error('Error fetching updated summary for UI:', error);
                     alert('Ошибка при обновлении данных выбора: ' + error);
                });
         } else {
             console.error("Не найден контейнер .selection-summary-content для обновления.");
         }
    }

    // Функция для прикрепления слушателей к кнопкам в summary (для кнопок x и clear)
    function attachSummaryButtonListeners() {
         const summaryButtons = document.querySelectorAll('.selection-summary-content .ajax-update-button');
         summaryButtons.forEach(button => {
             // Проверяем, не прикреплен ли слушатель уже
             if (!button.dataset.listenerAttached) {
                button.addEventListener('click', handleAjaxButtonClick);
                button.dataset.listenerAttached = 'true';
             }
         });
    }

     // Функция для обновления состояния кнопок генерации документов/очистки
    function updateDocumentButtonState() {
         const selectionSummary = document.querySelector('.selection-summary');
         // Селектор для всех кнопок/ссылок в document-buttons, которые могут быть disabled
         const buttonsToDisable = selectionSummary ? selectionSummary.querySelectorAll('.document-buttons .button, .document-buttons button.ajax-update-button') : [];

         // Проверяем наличие строк в таблице выбора summary tbody
         const totalItemsInSelection = selectionSummary ? selectionSummary.querySelector('.selection-summary-content tbody tr') : null;

         if (!totalItemsInSelection) {
             buttonsToDisable.forEach(button => {
                  button.classList.add('disabled');
                  // Удаляем слушатель клика только для AJAX кнопок
                  if (button.classList.contains('ajax-update-button')) {
                      // Проверяем, прикреплен ли слушатель, прежде чем удалять
                      if (button.dataset.listenerAttached) {
                           button.removeEventListener('click', handleAjaxButtonClick);
                           button.dataset.listenerAttached = 'false'; // Сбрасываем флаг
                      }
                  } else {
                       // Для обычных ссылок, используем onclick="return false;" в шаблоне
                       // Этот JS код не должен управлять их слушателями, только классом disabled
                  }
             });
         } else {
              buttonsToDisable.forEach(button => {
                  button.classList.remove('disabled');
                  if (button.classList.contains('ajax-update-button')) {
                       if (!button.dataset.listenerAttached || button.dataset.listenerAttached === 'false') {
                           button.addEventListener('click', handleAjaxButtonClick);
                           button.dataset.listenerAttached = 'true';
                       }
                  }
             });
         }
    }
    const initialAjaxButtons = document.querySelectorAll('.ajax-update-button');
    initialAjaxButtons.forEach(button => {
         if (!button.dataset.listenerAttached || button.dataset.listenerAttached === 'false') {
            button.addEventListener('click', handleAjaxButtonClick);
            button.dataset.listenerAttached = 'true';
         }
    });
    updateDocumentButtonState();

});