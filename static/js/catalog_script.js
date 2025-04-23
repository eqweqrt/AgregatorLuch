// catalog/static/js/catalog_script.js

document.addEventListener('DOMContentLoaded', function() {
    // Убедимся, что CSRF_TOKEN и UPDATE_SELECTION_URL доступны
    if (typeof CSRF_TOKEN === 'undefined') {
        console.error('CSRF_TOKEN is not defined! Make sure it is passed from the Django template.');
        alert('Ошибка инициализации: CSRF токен не найден.');
        // Блокировать функционал AJAX
        disableAjaxButtons(true);
        return;
    }
    if (typeof UPDATE_SELECTION_URL === 'undefined') {
        console.error('UPDATE_SELECTION_URL is not defined! Make sure it is passed from the Django template.');
        alert('Ошибка инициализации: URL обновления не найден.');
        // Блокировать функционал AJAX
        disableAjaxButtons(true);
        return;
    }
    console.log('AJAX variables available.');


    // === Хелпер функция для включения/отключения AJAX кнопок ===
    function disableAjaxButtons(disable) {
        const buttons = document.querySelectorAll('.ajax-update-button, .button-apply-prices');
        buttons.forEach(button => {
            if (disable) {
                button.classList.add('disabled');
                button.disabled = true;
            } else {
                // Неактивируем кнопки, которые должны быть неактивны из-за пустого выбора
                // Логика disabled для пустых кнопок уже в шаблоне selection_summary_partial.html
                // if (button.dataset.action !== 'clear' && !document.querySelector('.selection-summary-content table')) {
                //     // Если нет таблицы в сводке (выбор пуст), оставляем кнопки генерации неактивными
                // } else {
                     button.classList.remove('disabled');
                     button.disabled = false;
                // }
            }
        });
         // Отключение полей ввода цены тоже
         const priceInputs = document.querySelectorAll('.item-price-input');
         priceInputs.forEach(input => { input.disabled = disable; });

         console.log(`AJAX buttons and inputs ${disable ? 'disabled' : 'enabled'}.`);
    }


    // === Обработка кликов по кнопкам AJAX обновления (плюс/минус кол-ва, OK кол-ва, Удалить позицию, Очистить выбор) ===
    // Делегирование событий клика на body
    document.body.addEventListener('click', function(event) {
        const target = event.target;

        // Проверяем, является ли кликнутый элемент кнопкой с классом ajax-update-button
        if (target.classList.contains('ajax-update-button')) {
            const action = target.dataset.action;
            const modelId = target.dataset.modelId;

            // Проверяем, не отключена ли кнопка
            if (target.classList.contains('disabled')) {
                 console.log('Clicked disabled button:', action, modelId);
                 event.preventDefault(); // Предотвращаем действие
                 return;
            }

            console.log(`AJAX button clicked: Action=${action}, ModelID=${modelId}`);

            let quantityInput;
            let quantity;

            const postData = {
                'csrfmiddlewaretoken': CSRF_TOKEN,
                'action': action,
            };

            if (action !== 'clear') { // Для 'clear' не нужен model_id
                if (!modelId) {
                     console.error('Ошибка: Отсутствует data-model-id на кнопке для действия', action);
                     alert('Произошла внутренняя ошибка.');
                     return;
                }
                postData['model_id'] = modelId;

                // Для действия 'set' (установка количества из input)
                if (action === 'set') {
                    quantityInput = document.querySelector(`.quantity-input[data-model-id="${modelId}"]`);
                    if (quantityInput) {
                        quantity = quantityInput.value;
                        // Проверяем, что количество - неотрицательное целое число
                        if (quantity === '' || quantity === null || isNaN(quantity) || parseInt(quantity, 10) < 0 || String(parseFloat(quantity)) !== String(parseInt(quantity, 10))) {
                             alert('Введите корректное неотрицательное целое число для количества.');
                             // Опционально: можно сбросить значение поля
                             // quantityInput.value = quantityInput.defaultValue;
                             return;
                        }
                        postData['quantity'] = quantity;
                    } else {
                        console.error('Ошибка: Не найдено поле количества для модели ID', modelId);
                         alert('Произошла внутренняя ошибка.');
                        return;
                    }
                }
                // Действия 'add', 'remove', 'remove_all' не требуют отправки quantity
            } else { // action === 'clear'
                 if (!confirm('Вы уверены, что хотите очистить весь выбор?')) {
                     event.preventDefault();
                     return;
                 }
            }

            // Если дошли сюда, значит, все проверки пройдены, отправляем AJAX
            // Оборачиваем postData в URLSearchParams
            sendAjaxUpdate(new URLSearchParams(postData));

            event.preventDefault(); // Предотвращаем стандартное действие
        }
    });

    // === Обработка клика по кнопке "Применить цены" ===
    // Делегирование событий клика на body
document.body.addEventListener('click', function(event) {
        const target = event.target;

        // Проверяем, является ли кликнутый элемент кнопкой "Применить цены"
        if (target.classList.contains('button-apply-prices')) {

            // === ДОБАВЬТЕ ЭТОТ ЛОГ СЮДА ===
            console.log('>>> Нажата кнопка "Применить цены". Проверяем код обработчика...');
            // =============================

            // Проверяем, не отключена ли кнопка
            if (target.classList.contains('disabled')) {
                 console.log('Clicked disabled Apply Prices button. Preventing action.');
                 event.preventDefault();
                 return; // Код прерывается здесь, если кнопка disabled
            }

            console.log('Apply Prices button clicked. (Button is not disabled)');

            const priceInputs = document.querySelectorAll('.selection-summary-content .item-price-input');

            // === ДОБАВЬТЕ ЭТОТ ЛОГ ===
            console.log('Найдено полей ввода цены:', priceInputs.length);
            // =====================

            const pricesToUpdate = {};
            let isValid = true;
            // let hasChanges = false; // Флаг, чтобы проверить, были ли изменения цен вообще

            // Собираем данные со всех полей ввода цены
            priceInputs.forEach(input => {
                 // === ДОБАВЬТЕ ЭТОТ ЛОГ ВНУТРИ ЦИКЛА ===
                 console.log('Обработка поля цены для modelId:', input.dataset.modelId, 'value:', input.value);
                 // ===================================

                const modelId = input.dataset.modelId;
                const newPrice = input.value.trim();

                 // Проверяем, что цена - неотрицательное число или пустая строка
                 if (newPrice !== '' && (isNaN(newPrice) || parseFloat(newPrice) < 0)) {
                      alert(`Некорректное значение цены "${newPrice}" для позиции (ID: ${modelId}). Введите неотрицательное число.`);
                      isValid = false;
                      // break; // Нельзя использовать break в forEach, нужно использовать флаг и return из forEach callback
                      return; // Прерывает только выполнение callback для текущего элемента
                 } else {
                      // Если валидно, сохраняем (пустая строка или число)
                      pricesToUpdate[modelId] = newPrice;
                      // if (newPrice !== '') hasChanges = true; // Грубая проверка изменений
                 }
            });

            // Если isValid стал false во время forEach, прерываемся
            if (!isValid) {
                console.log('Валидация цен провалилась. Запрос не отправлен.');
                event.preventDefault();
                return; // Код прерывается здесь, если валидация не пройдена
            }

            // Если нет товаров в выборе (нет полей input price), кнопка должна быть неактивна в HTML
            // Но на всякий случай проверяем в JS
            if (Object.keys(pricesToUpdate).length === 0) {
                console.log('Нет позиций для обновления цен (pricesToUpdate пуст). Запрос не отправлен.');
                // alert('Нет выбранных позиций для применения цен.'); // Можно добавить уведомление
                event.preventDefault();
                return; // Код прерывается здесь, если нет цен для отправки
            }

            // ... (остальной код формирования postData и вызова sendAjaxUpdate) ...

            const postData = new URLSearchParams();
            postData.append('csrfmiddlewaretoken', CSRF_TOKEN);
            postData.append('action', 'apply_prices');

            for (const modelId in pricesToUpdate) {
                if (pricesToUpdate.hasOwnProperty(modelId)) {
                     postData.append(modelId, pricesToUpdate[modelId]);
                }
            }

            // === ДОБАВЬТЕ ЭТОТ ЛОГ ПЕРЕД ВЫЗОВОМ sendAjaxUpdate ===
            console.log('Валидация пройдена. Данные для отправки:', Object.fromEntries(postData.entries())); // Преобразуем для удобства чтения в консоли
            console.log('Вызов sendAjaxUpdate...');
            // ======================================================

            sendAjaxUpdate(postData); // Этот вызов должен инициировать Network активность

            event.preventDefault(); // Предотвращаем стандартное действие
        }
    });


    // === Функция для отправки AJAX запроса и обработки ответа ===
    // Принимает данные в формате URLSearchParams или FormData
    function sendAjaxUpdate(postData) {
        console.log('Отправка AJAX запроса:', postData);
        // Отключаем кнопки и поля ввода на время выполнения запроса
        disableAjaxButtons(true);


        fetch(UPDATE_SELECTION_URL, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest', // Для определения AJAX на сервере
                // Content-Type для URLSearchParams устанавливается автоматически как application/x-www-form-urlencoded
            },
            body: postData // URLSearchParams объект или FormData
        })
        .then(response => {
            console.log('Получен ответ AJAX. Status:', response.status);
            // Читаем текст ответа независимо от статуса, чтобы получить сообщения об ошибках или HTML
            return response.text().then(text => {
                 if (response.ok) {
                      return { html: text, status: response.status };
                 } else {
                     // Пробуем распарсить JSON, если ответ в формате JSON (для более структурированных ошибок)
                     try {
                          const errorJson = JSON.parse(text);
                          return { message: errorJson.error || text, status: response.status };
                     } catch (e) {
                          // Если не JSON, используем просто текст
                          return { message: text || response.statusText, status: response.status };
                     }
                 }
            });
        })
        .then(data => {
             // Включаем кнопки и поля ввода обратно
             disableAjaxButtons(false);

             // Обработка успешного ответа (HTTP 200)
             if (data.status >= 200 && data.status < 300) { // Успешные статусы 2xx
                 // === Обновляем блок сводки на странице ===
                 const summaryContentDiv = document.querySelector('.selection-summary-content');
                 if (summaryContentDiv) {
                     summaryContentDiv.innerHTML = data.html; // Заменяем содержимое на полученный HTML
                     console.log('Сводка выбора успешно обновлена AJAX-ом.');
                     // Сообщения Django, переданные через ajax_messages, теперь в DOM
                     // Можно добавить JS для их автоматического скрытия через несколько секунд
                     hideAjaxMessages();
                 } else {
                     console.error('Не найден div .selection-summary-content для обновления.');
                     alert('Произошла внутренняя ошибка при обновлении интерфейса.');
                 }
             } else {
                 // Обработка ошибок, которые вернул сервер (статус не 2xx)
                 console.error('Ошибка при обновлении выбора:', data.status, data.message);
                 alert('Ошибка при обновлении выбора: ' + data.message);
                 // Опционально: перезагрузка страницы при ошибке
                 // location.reload();
             }
        })
        .catch(error => {
            // Включаем кнопки и поля ввода обратно при ошибке
             disableAjaxButtons(false);
            // Обработка сетевых ошибок или ошибок в процессе fetch/then
            console.error('Сетевая ошибка или ошибка в обработчике .then():', error);
            alert('Произошла ошибка при выполнении запроса: ' + error);
             // Опционально: перезагрузка страницы при ошибке
             // location.reload();
        });
    }

    // Хелпер функция для скрытия AJAX сообщений
    function hideAjaxMessages() {
        // Находим контейнер сообщений внутри обновленного блока сводки
        const messageContainer = document.querySelector('.selection-summary-content .messages.ajax-messages');
        if (messageContainer) {
             const messages = messageContainer.querySelectorAll('li');
             messages.forEach(msg => {
                 // Удаляем через несколько секунд
                 setTimeout(() => {
                     // Добавляем плавное исчезновение
                     msg.style.transition = 'opacity 0.5s ease-in-out';
                     msg.style.opacity = 0;
                     // Удаляем элемент из DOM после завершения анимации
                     // Убедимся, что элемент все еще присоединен к DOM перед удалением
                     msg.addEventListener('transitionend', () => {
                         if (msg.parentNode) {
                             msg.parentNode.removeChild(msg);
                         }
                         // Если после удаления всех сообщений контейнер пуст, удалить и контейнер
                         if (messageContainer && messageContainer.children.length === 0 && messageContainer.parentNode) {
                              messageContainer.parentNode.removeChild(messageContainer);
                         }
                     });
                 }, 5000); // Скрыть через 5 секунд
             });
        }
    }


    // === Дополнительная функция для сворачивания/разворачивания разделов ===
    // (Оставляем ваш существующий код, если он работает)
    const toggleElements = document.querySelectorAll('.toggle-text');

    toggleElements.forEach(function(element) {
        element.addEventListener('click', function() {
            const parentLi = this.closest('li');
            if (!parentLi) return;

            const collapsibleContent = parentLi.querySelector('.collapsible');
            const toggleIcon = this.previousElementSibling;

            if (collapsibleContent && toggleIcon) {
                const isCollapsed = collapsibleContent.classList.contains('collapsed');

                if (isCollapsed) {
                    collapsibleContent.classList.remove('collapsed');
                    toggleIcon.classList.remove('collapsed');
                    toggleIcon.textContent = '▼';
                } else {
                    collapsibleContent.classList.add('collapsed');
                    toggleIcon.classList.add('collapsed');
                    toggleIcon.textContent = '►';
                }
            }
        });
    });
});