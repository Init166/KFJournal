// static/admin_panel/js/admin_panel.js

// Глобальные переменные
let currentSelectedItem = null;
let sortableInstances = [];

// Инициализация дерева баз данных
function initDatabaseTree() {
    // Восстанавливаем состояние из localStorage
    const expandedItems = JSON.parse(localStorage.getItem('expandedTreeItems') || '[]');
    expandedItems.forEach(id => {
        const item = document.querySelector(`[data-id="${id}"] .tree-children`);
        if (item) {
            item.style.display = 'block';
            const toggle = item.closest('.tree-item')?.querySelector('.tree-toggle');
            if (toggle) toggle.classList.add('expanded');
        }
    });
}

// Переключение раскрытия элемента дерева
function toggleTreeItem(element) {
    const treeItem = element.closest('.tree-item');
    const children = treeItem.querySelector('.tree-children');
    const toggle = treeItem.querySelector('.tree-toggle');
    
    if (children.style.display === 'none') {
        children.style.display = 'block';
        toggle.classList.add('expanded');
        
        // Сохраняем состояние
        saveExpandedState(treeItem.dataset.id, true);
    } else {
        children.style.display = 'none';
        toggle.classList.remove('expanded');
        
        // Сохраняем состояние
        saveExpandedState(treeItem.dataset.id, false);
    }
}

// Сохранение состояния раскрытых элементов
function saveExpandedState(id, isExpanded) {
    let expandedItems = JSON.parse(localStorage.getItem('expandedTreeItems') || '[]');
    
    if (isExpanded) {
        if (!expandedItems.includes(id)) {
            expandedItems.push(id);
        }
    } else {
        expandedItems = expandedItems.filter(itemId => itemId !== id);
    }
    
    localStorage.setItem('expandedTreeItems', JSON.stringify(expandedItems));
}

// Выбор элемента базы данных
function selectDatabaseItem(element, type, id) {
    // Снимаем выделение с предыдущего элемента
    if (currentSelectedItem) {
        currentSelectedItem.classList.remove('active');
    }
    
    // Выделяем текущий элемент
    element.classList.add('active');
    currentSelectedItem = element;
    
    // Загружаем содержимое
    loadDatabaseContent(type, id);
}


// Загрузка содержимого базы данных
function loadDatabaseContent(type, id) {
    const contentContainer = document.getElementById('contentContainer');
    const contentTitle = document.getElementById('selectedItemTitle');
    const contentPath = document.getElementById('selectedItemPath');
    const contentActions = document.getElementById('contentActions');
    
    // Показываем загрузку
    contentContainer.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div><p class="mt-3">Загрузка данных...</p></div>';
    
    // Делаем AJAX запрос
    fetch(`/admin-panel/api/content/?type=${type}&id=${id}`)
        .then(response => response.json())
        .then(data => {
            // Обновляем заголовок
            contentTitle.textContent = data.title;
            contentPath.textContent = data.path;
            
            // Обновляем кнопки действий
            updateActionButtons(type, data);
            
            // Обновляем контент
            renderContent(type, data, contentContainer);
        })
        .catch(error => {
            console.error('Error:', error);
            contentContainer.innerHTML = '<div class="alert alert-danger">Ошибка загрузки данных</div>';
        });
}

// Обновление кнопок действий
function updateActionButtons(type, data) {
    const actions = document.getElementById('contentActions');
    
    if (type === 'group') {
        actions.innerHTML = `
            <button class="action-btn action-btn-success" onclick="openCreateModal('student')">
                <i class="bi bi-person-plus"></i> Добавить студента
            </button>
            <button class="action-btn action-btn-primary" onclick="openCreateModal('bulk')">
                <i class="bi bi-file-earmark-spreadsheet"></i> Импорт из Excel
            </button>
            <button class="action-btn action-btn-outline" onclick="exportGroup(${data.id})">
                <i class="bi bi-download"></i> Экспорт
            </button>
        `;
    } else if (type === 'department') {
        actions.innerHTML = `
            <button class="action-btn action-btn-success" onclick="openCreateModal('employee')">
                <i class="bi bi-person-badge"></i> Добавить сотрудника
            </button>
            <button class="action-btn action-btn-outline" onclick="openCreateModal('subdepartment')">
                <i class="bi bi-folder-plus"></i> Добавить подотдел
            </button>
        `;
    } else {
        actions.innerHTML = `
            <button class="action-btn action-btn-success" onclick="openCreateModal('${type}')">
                <i class="bi bi-plus-circle"></i> Создать
            </button>
            <button class="action-btn action-btn-outline" onclick="openEditModal()">
                <i class="bi bi-pencil"></i> Редактировать
            </button>
            <button class="action-btn action-btn-danger" onclick="confirmDelete()">
                <i class="bi bi-trash"></i> Удалить
            </button>
        `;
    }
}

// static/admin_panel/js/admin_panel.js - обновляем renderContent

function renderContent(type, data, container) {
    if (type === 'group' && data.students) {
        // Сортируем студентов по алфавиту
        const sortedStudents = [...data.students].sort((a, b) => 
            a.full_name.localeCompare(b.full_name, 'ru')
        );
        
        let html = `
            <div class="d-flex justify-content-between align-items-center mb-3">
                <div>
                    <span class="badge bg-primary">Всего студентов: ${sortedStudents.length}</span>
                </div>
                <div>
                    <button class="btn btn-sm btn-outline-secondary" onclick="sortStudents('name')">
                        <i class="bi bi-sort-alpha-down"></i> По алфавиту
                    </button>
                </div>
            </div>
            <div class="table-responsive">
                <table class="users-table">
                    <thead>
                        <tr>
                            <th style="width: 60px">#</th>
                            <th style="width: 30px"></th>
                            <th>ФИО</th>
                            <th>Логин</th>
                            <th>Email</th>
                            <th>Телефон</th>
                            <th>Статус</th>
                            <th>Действия</th>
                        </tr>
                    </thead>
                    <tbody id="studentTableBody">
        `;
        
        sortedStudents.forEach((student, index) => {
            html += `
                <tr draggable="true" ondragstart="dragStart(event)" ondragend="dragEnd(event)" 
                    data-id="${student.id}" data-type="student" data-name="${student.full_name}">
                    <td><span class="badge bg-light text-dark">${index + 1}</span></td>
                    <td>
                        <i class="bi bi-grip-vertical text-muted" style="cursor: move;"></i>
                    </td>
                    <td>
                        <div class="d-flex align-items-center">
                            <i class="bi bi-person-circle me-2 text-primary"></i>
                            ${student.full_name}
                            ${student.is_elder ? '<span class="badge-elder ms-2">Староста ⭐</span>' : ''}
                        </div>
                    </td>
                    <td><code>${student.login}</code></td>
                    <td>${student.email || '<span class="text-muted">—</span>'}</td>
                    <td>${student.phone || '<span class="text-muted">—</span>'}</td>
                    <td>
                        <span class="badge ${student.is_active ? 'bg-success' : 'bg-secondary'}">
                            ${student.is_active ? 'Активен' : 'Неактивен'}
                        </span>
                    </td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="openEditModal('student', ${student.id})">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="openDeleteModal('student', ${student.id})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        container.innerHTML = html;
        
        // Инициализируем Drag & Drop для студентов
        initStudentDragAndDrop();
        
    } else if (type === 'group' && (!data.students || data.students.length === 0)) {
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-people display-1 text-muted"></i>
                <h3 class="mt-3">В группе пока нет студентов</h3>
                <p class="text-muted">Нажмите "Добавить студента", чтобы создать первую запись</p>
                <button class="btn btn-primary mt-3" onclick="openCreateModal('student', ${data.id})">
                    <i class="bi bi-person-plus"></i> Добавить первого студента
                </button>
            </div>
        `;
    }
}


// Инициализация Drag & Drop
function initStudentDragAndDrop() {
    const table = document.querySelector('.users-table tbody');
    if (!table) return;
    
    Sortable.create(table, {
        animation: 150,
        handle: '.bi-grip-vertical',
        draggable: 'tr',
        onEnd: function(evt) {
            const studentId = evt.item.dataset.id;
            const fromGroup = currentSelectedItem.dataset.id;
            
            // Здесь будет логика перемещения между группами
            console.log(`Student ${studentId} moved within group ${fromGroup}`);
        }
    });
}

// Меж-табличный Drag & Drop
function initDragAndDrop() {
    const groups = document.querySelectorAll('[data-type="group"] .tree-item-header');
    
    groups.forEach(group => {
        group.addEventListener('dragover', (e) => {
            e.preventDefault();
            group.classList.add('drag-over');
        });
        
        group.addEventListener('dragleave', () => {
            group.classList.remove('drag-over');
        });
        
        group.addEventListener('drop', (e) => {
            e.preventDefault();
            group.classList.remove('drag-over');
            
            const studentId = e.dataTransfer.getData('text/plain');
            const targetGroupId = group.closest('[data-type="group"]').dataset.id;
            
            // Перемещаем студента
            moveStudent(studentId, targetGroupId);
        });
    });
}

// static/admin_panel/js/admin_panel.js - улучшенный Drag & Drop

function initDragAndDrop() {
    // Делаем все группы и курсы принимающими для drag & drop
    const dropTargets = document.querySelectorAll([
        '[data-type="group"] .tree-item-header',
        '[data-type="course"] .tree-item-header',
        '[data-type="form"] .tree-item-header',
        '[data-type="level"] .tree-item-header'
    ].join(','));
    
    dropTargets.forEach(target => {
        target.addEventListener('dragover', (e) => {
            e.preventDefault();
            target.classList.add('drag-over');
        });
        
        target.addEventListener('dragleave', () => {
            target.classList.remove('drag-over');
        });
        
        target.addEventListener('drop', (e) => {
            e.preventDefault();
            target.classList.remove('drag-over');
            
            const draggedData = e.dataTransfer.getData('text/plain');
            const [draggedType, draggedId] = draggedData.split(':');
            const targetItem = target.closest('[data-type]');
            const targetType = targetItem.dataset.type;
            const targetId = targetItem.dataset.id;
            
            // Перемещаем элемент
            moveItem(draggedType, draggedId, targetType, targetId);
        });
    });
}

function moveItem(itemType, itemId, targetType, targetId) {
    fetch('/admin-panel/api/move-item/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            type: itemType,
            item_id: parseInt(itemId),
            target_type: targetType,
            target_id: parseInt(targetId)
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('✅ Элемент успешно перемещен', 'success');
            // Обновляем содержимое текущей папки
            if (currentItemType && currentItemId) {
                loadDatabaseContent(currentItemType, currentItemId);
            }
            // Перезагружаем дерево, чтобы обновить счетчики
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification('❌ Ошибка при перемещении: ' + data.error, 'danger');
        }
    });
}

function initStudentDragAndDrop() {
    const tbody = document.getElementById('studentTableBody');
    if (!tbody) return;
    
    new Sortable(tbody, {
        animation: 150,
        handle: '.bi-grip-vertical',
        draggable: 'tr',
        group: {
            name: 'students',
            pull: true,
            revertClone: false
        },
        onEnd: function(evt) {
            const studentId = evt.item.dataset.id;
            const studentName = evt.item.dataset.name;
            
            // Если элемент был перемещен в другой список (группу)
            if (evt.to.id !== evt.from.id) {
                showNotification(
                    `🎓 Студент ${studentName} перемещен. Выберите целевую группу в левой панели и нажмите Ctrl+V`,
                    'info'
                );
            }
        }
    });
}

// Поддержка Ctrl+V для вставки студентов в группу
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.key === 'v' && currentItemType === 'group') {
        e.preventDefault();
        // Здесь можно реализовать вставку скопированного студента
        const clipboardData = e.clipboardData || window.clipboardData;
        if (clipboardData) {
            const pastedData = clipboardData.getData('text');
            if (pastedData.startsWith('student:')) {
                const studentId = pastedData.split(':')[1];
                moveItem('student', studentId, 'group', currentItemId);
            }
        }
    }
});

// static/admin_panel/js/admin_panel.js - обновляем dragStart

function dragStart(event) {
    const row = event.target.closest('tr');
    const itemType = row.dataset.type;
    const itemId = row.dataset.id;
    
    // Передаем и тип, и ID
    event.dataTransfer.setData('text/plain', `${itemType}:${itemId}`);
    event.dataTransfer.effectAllowed = 'move';
    
    row.classList.add('dragging');
}

// Также добавляем dragStart для элементов дерева
function makeTreeItemsDraggable() {
    const draggableItems = document.querySelectorAll([
        '[data-type="group"] .tree-item-header',
        '[data-type="student"]'
    ].join(','));
    
    draggableItems.forEach(item => {
        item.draggable = true;
        item.addEventListener('dragstart', (e) => {
            const treeItem = e.target.closest('[data-type]');
            if (treeItem) {
                e.dataTransfer.setData('text/plain', 
                    `${treeItem.dataset.type}:${treeItem.dataset.id}`
                );
                e.dataTransfer.effectAllowed = 'move';
            }
        });
    });
}

// Функции для модальных окон
function openCreateModal(type) {
    const modal = document.getElementById('itemModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    
    modalTitle.textContent = `Создание ${getTypeName(type)}`;
    
    // Генерируем форму в зависимости от типа
    modalBody.innerHTML = generateCreateForm(type);
    
    modal.style.display = 'block';
}

function closeModal() {
    const modal = document.getElementById('itemModal');
    modal.style.display = 'none';
}

// Закрытие модального окна по клику вне его
window.onclick = function(event) {
    const modal = document.getElementById('itemModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}

// Генерация формы создания
function generateCreateForm(type) {
    switch(type) {
        case 'student':
            return `
                <form id="createForm" onsubmit="submitCreateForm(event)">
                    <div class="form-group">
                        <label>ФИО студента</label>
                        <input type="text" class="form-control" name="full_name" required>
                    </div>
                    <div class="form-group">
                        <label>Логин</label>
                        <input type="text" class="form-control" name="login" required>
                    </div>
                    <div class="form-group">
                        <label>Пароль</label>
                        <input type="password" class="form-control" name="password" required>
                    </div>
                    <div class="form-group">
                        <label>Email</label>
                        <input type="email" class="form-control" name="email">
                    </div>
                    <div class="form-group">
                        <label>Телефон</label>
                        <input type="tel" class="form-control" name="phone">
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="is_elder">
                            Назначить старостой
                        </label>
                    </div>
                    <button type="submit" class="action-btn action-btn-primary w-100">Создать</button>
                </form>
            `;
        case 'employee':
            return `
                <form id="createForm" onsubmit="submitCreateForm(event)">
                    <div class="form-group">
                        <label>ФИО сотрудника</label>
                        <input type="text" class="form-control" name="full_name" required>
                    </div>
                    <div class="form-group">
                        <label>Логин</label>
                        <input type="text" class="form-control" name="login" required>
                    </div>
                    <div class="form-group">
                        <label>Пароль</label>
                        <input type="password" class="form-control" name="password" required>
                    </div>
                    <div class="form-group">
                        <label>Должность</label>
                        <select class="form-control" name="position">
                            <option value="teacher">Преподаватель</option>
                            <option value="dean">Декан</option>
                            <option value="deputy_dean">Зам. декана</option>
                            <option value="methodist">Методист</option>
                            <option value="admin">Администратор</option>
                            <option value="other">Другое</option>
                        </select>
                    </div>
                    <button type="submit" class="action-btn action-btn-primary w-100">Создать</button>
                </form>
            `;
        // ... другие типы
        default:
            return '<p>Форма для данного типа находится в разработке</p>';
    }
}

// Вспомогательные функции
function getTypeName(type) {
    const names = {
        'level': 'уровня образования',
        'form': 'формы обучения',
        'course': 'курса',
        'group': 'группы',
        'student': 'студента',
        'department': 'отдела',
        'employee': 'сотрудника'
    };
    return names[type] || type;
}

// static/admin_panel/js/admin_panel.js - добавьте и обновите функции

// Улучшенная форма создания студента с нумерацией и сортировкой
function generateCreateForm(type, parentId) {
    switch(type) {
        case 'student':
            return `
                <form id="createForm" onsubmit="submitCreateForm(event, 'student', ${parentId})">
                    <div class="form-group">
                        <label>👤 ФИО студента</label>
                        <input type="text" class="form-control" name="full_name" required 
                               placeholder="Иванов Иван Иванович">
                    </div>
                    <div class="form-group">
                        <label>🔐 Логин</label>
                        <input type="text" class="form-control" name="login" required 
                               placeholder="ivanov.ii" id="loginInput">
                    </div>
                    <div class="form-group">
                        <label>📧 Email</label>
                        <input type="email" class="form-control" name="email" 
                               placeholder="student@example.com">
                    </div>
                    <div class="form-group">
                        <label>📱 Телефон</label>
                        <input type="tel" class="form-control" name="phone" 
                               placeholder="+7 (999) 123-45-67">
                    </div>
                    <div class="form-check mb-3">
                        <input type="checkbox" class="form-check-input" name="is_elder" id="isElder">
                        <label class="form-check-label" for="isElder">
                            ⭐ Назначить старостой
                        </label>
                    </div>
                    <div class="alert alert-info">
                        <small>
                            <i class="bi bi-info-circle"></i>
                            Пароль будет сгенерирован автоматически и отправлен студенту
                        </small>
                    </div>
                    <button type="submit" class="action-btn action-btn-primary w-100">
                        <i class="bi bi-person-plus"></i> Создать студента
                    </button>
                </form>
                <script>
                    // Автоматическое заполнение логина из ФИО
                    document.querySelector('input[name="full_name"]').addEventListener('input', function(e) {
                        const fullName = e.target.value;
                        const loginInput = document.querySelector('input[name="login"]');
                        if (fullName && !loginInput.value) {
                            // Транслитерация ФИО в логин
                            const translit = {
                                'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e',
                                'ё': 'e', 'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k',
                                'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r',
                                'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts',
                                'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '',
                                'э': 'e', 'ю': 'yu', 'я': 'ya'
                            };
                            
                            let login = fullName.toLowerCase()
                                .split(' ')
                                .map((part, index) => {
                                    let transliterated = '';
                                    for (let char of part) {
                                        transliterated += translit[char] || char;
                                    }
                                    return index === 0 ? transliterated : transliterated[0];
                                })
                                .join('.');
                            
                            loginInput.value = login;
                        }
                    });
                <\/script>
            `;
            
        case 'level':
            return `
                <form id="createForm" onsubmit="submitCreateForm(event, 'level')">
                    <div class="form-group">
                        <label>🎓 Название уровня образования</label>
                        <input type="text" class="form-control" name="name" required 
                               placeholder="Например: Бакалавриат, Магистратура, Специалитет">
                    </div>
                    <div class="form-group">
                        <label>🔢 Порядок сортировки</label>
                        <input type="number" class="form-control" name="order" value="1" min="1">
                        <small class="text-muted">Чем меньше число, тем выше в списке</small>
                    </div>
                    <button type="submit" class="action-btn action-btn-primary w-100">
                        <i class="bi bi-database-add"></i> Создать уровень образования
                    </button>
                </form>
            `;
            
        case 'form':
            return `
                <form id="createForm" onsubmit="submitCreateForm(event, 'form', ${parentId})">
                    <div class="form-group">
                        <label>📚 Форма обучения</label>
                        <input type="text" class="form-control" name="name" required 
                               placeholder="Очная форма, Заочная форма, Очно-заочная форма">
                    </div>
                    <div class="form-group">
                        <label>🔢 Порядок сортировки</label>
                        <input type="number" class="form-control" name="order" value="1" min="1">
                    </div>
                    <button type="submit" class="action-btn action-btn-primary w-100">
                        <i class="bi bi-folder-plus"></i> Создать форму обучения
                    </button>
                </form>
            `;
            
        case 'course':
            return `
                <form id="createForm" onsubmit="submitCreateForm(event, 'course', ${parentId})">
                    <div class="form-group">
                        <label>📖 Номер курса</label>
                        <input type="number" class="form-control" name="number" required 
                               placeholder="1" min="1" max="6">
                    </div>
                    <button type="submit" class="action-btn action-btn-primary w-100">
                        <i class="bi bi-layers"></i> Создать курс
                    </button>
                </form>
            `;
            
        case 'group':
            return `
                <form id="createForm" onsubmit="submitCreateForm(event, 'group', ${parentId})">
                    <div class="form-group">
                        <label>👥 Название группы</label>
                        <input type="text" class="form-control" name="name" required 
                               placeholder="Например: СПД-103, Ю-201, ПД-101">
                    </div>
                    <button type="submit" class="action-btn action-btn-primary w-100">
                        <i class="bi bi-people"></i> Создать группу
                    </button>
                </form>
            `;
            
        default:
            return '<p class="text-center text-muted py-4">Форма для данного типа находится в разработке</p>';
    }
}

function moveStudent(studentId, targetGroupId) {
    fetch('/admin-panel/api/move-student/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            student_id: studentId,
            target_group_id: targetGroupId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Студент успешно перемещен', 'success');
            // Обновляем содержимое
            if (currentSelectedItem) {
                const type = currentSelectedItem.closest('[data-type]').dataset.type;
                const id = currentSelectedItem.closest('[data-type]').dataset.id;
                loadDatabaseContent(type, id);
            }
        } else {
            showNotification('Ошибка при перемещении', 'danger');
        }
    });
}

function showNotification(message, type) {
    // Создаем уведомление Bootstrap Toast
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0 position-fixed bottom-0 end-0 m-3`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    document.body.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// Получение CSRF токена
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

// static/admin_panel/js/admin_panel.js - добавляем новые функции

// ==================== НАВИГАЦИЯ КАК В ПРОВОДНИКЕ ====================

let navigationStack = [];
let currentPosition = -1;
let currentFolderType = null;
let currentFolderId = null;

function navigateTo(type, id, title) {
    // Сохраняем в историю
    if (currentPosition < navigationStack.length - 1) {
        navigationStack = navigationStack.slice(0, currentPosition + 1);
    }
    
    navigationStack.push({
        type: type,
        id: id,
        title: title,
        timestamp: new Date().getTime()
    });
    
    currentPosition = navigationStack.length - 1;
    
    // Загружаем содержимое
    loadFolderContent(type, id);
    
    // Обновляем кнопки навигации
    updateNavigationButtons();
}

function goBack() {
    if (currentPosition > 0) {
        currentPosition--;
        const item = navigationStack[currentPosition];
        loadFolderContent(item.type, item.id);
        updateNavigationButtons();
    }
}

function goForward() {
    if (currentPosition < navigationStack.length - 1) {
        currentPosition++;
        const item = navigationStack[currentPosition];
        loadFolderContent(item.type, item.id);
        updateNavigationButtons();
    }
}

function goUp() {
    if (currentFolderType && currentFolderId) {
        // Определяем родительскую папку
        fetch(`/admin-panel/api/folder-content/?type=${currentFolderType}&id=${currentFolderId}`)
            .then(response => response.json())
            .then(data => {
                if (data.path && data.path.length > 1) {
                    const parent = data.path[data.path.length - 2];
                    navigateTo(parent.type, parent.id, parent.name);
                }
            });
    }
}

function updateNavigationButtons() {
    document.getElementById('backBtn').disabled = currentPosition <= 0;
    document.getElementById('forwardBtn').disabled = currentPosition >= navigationStack.length - 1;
    document.getElementById('upBtn').disabled = !currentFolderType || !currentFolderId;
}

function loadFolderContent(type, id) {
    currentFolderType = type;
    currentFolderId = id;
    
    fetch(`/admin-panel/api/folder-content/?type=${type}&id=${id}`)
        .then(response => response.json())
        .then(data => {
            renderFolderContent(data);
            updatePathBreadcrumb(data.path);
        });
}

function renderFolderContent(data) {
    const container = document.getElementById('contentContainer');
    
    if (data.type === 'group') {
        // Отображаем студентов как в проводнике
        renderStudentsGrid(data.items);
    } else {
        // Отображаем папки как в проводнике
        renderFoldersGrid(data.items, data.type);
    }
}

function renderFoldersGrid(items, parentType) {
    let html = '<div class="folders-grid">';
    
    items.forEach(item => {
        html += `
            <div class="folder-item" ondblclick="navigateTo('${item.type}', ${item.id}, '${item.name}')">
                <div class="folder-icon">
                    <i class="${item.icon}"></i>
                </div>
                <div class="folder-name" ondblclick="event.stopPropagation(); renameItem('${item.type}', ${item.id})">
                    ${item.name}
                </div>
                <div class="folder-actions">
                    <button class="folder-btn" onclick="event.stopPropagation(); openCreateModal('${item.type.slice(0,-1)}', ${item.id})">
                        <i class="bi bi-plus-circle"></i>
                    </button>
                    <button class="folder-btn" onclick="event.stopPropagation(); openDeleteModal('${item.type}', ${item.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
                <div class="folder-stats">
                    <span class="badge bg-secondary">${item.count || 0}</span>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

function renderStudentsGrid(students) {
    let html = `
        <div class="students-header">
            <span>Всего студентов: <strong>${students.length}</strong></span>
            <div class="sort-options">
                <select onchange="sortStudents(this.value)">
                    <option value="name">По ФИО</option>
                    <option value="login">По логину</option>
                    <option value="status">По статусу</option>
                </select>
            </div>
        </div>
        <div class="students-grid">
    `;
    
    students.forEach((student, index) => {
        html += `
            <div class="student-card" draggable="true" 
                 ondragstart="dragStudentStart(event, ${student.id})"
                 ondragend="dragEnd(event)">
                <div class="student-number">${index + 1}</div>
                <div class="student-avatar">
                    <i class="bi bi-person-circle"></i>
                </div>
                <div class="student-info">
                    <div class="student-name">
                        ${student.full_name}
                        ${student.is_elder ? '<span class="badge-elder">Староста</span>' : ''}
                    </div>
                    <div class="student-details">
                        <span><i class="bi bi-box-arrow-in-right"></i> ${student.login}</span>
                        ${student.email ? `<span><i class="bi bi-envelope"></i> ${student.email}</span>` : ''}
                    </div>
                </div>
                <div class="student-actions">
                    <button class="btn-icon" onclick="openEditModal('student', ${student.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn-icon" onclick="openDeleteModal('student', ${student.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

// ==================== ПЕРЕИМЕНОВАНИЕ ДВОЙНЫМ КЛИКОМ ====================

function renameItem(type, id) {
    const element = event.target.closest('.folder-name');
    const oldName = element.textContent.trim();
    
    const input = document.createElement('input');
    input.type = 'text';
    input.value = oldName;
    input.className = 'rename-input';
    
    element.innerHTML = '';
    element.appendChild(input);
    input.focus();
    
    input.addEventListener('blur', () => {
        saveRename(type, id, input.value, element, oldName);
    });
    
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            saveRename(type, id, input.value, element, oldName);
        }
    });
}

function saveRename(type, id, newName, element, oldName) {
    fetch('/admin-panel/api/rename/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            type: type,
            id: id,
            name: newName
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            element.innerHTML = newName;
            showNotification(`✅ Переименовано: "${oldName}" → "${newName}"`, 'success');
            
            // Обновляем содержимое папки
            if (currentFolderType && currentFolderId) {
                loadFolderContent(currentFolderType, currentFolderId);
            }
        } else {
            element.innerHTML = oldName;
            showNotification('❌ Ошибка при переименовании', 'danger');
        }
    });
}

// ==================== ПОИСК (ЛУПА) ====================

let searchTimeout = null;

function initSearch() {
    const searchInput = document.getElementById('searchInput');
    
    searchInput.addEventListener('input', function(e) {
        clearTimeout(searchTimeout);
        
        const query = e.target.value.trim();
        
        if (query.length < 2) {
            hideSearchResults();
            return;
        }
        
        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 300);
    });
}

function performSearch(query) {
    fetch(`/admin-panel/api/search/?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            showSearchResults(data.results, data.count);
        });
}

function showSearchResults(results, total) {
    let resultsHtml = `
        <div class="search-results">
            <div class="search-results-header">
                <span>Найдено: ${total}</span>
                <button onclick="hideSearchResults()">✕</button>
            </div>
    `;
    
    results.forEach(student => {
        resultsHtml += `
            <div class="search-result-item" onclick="navigateToStudent(${student.id})">
                <i class="bi bi-person-circle"></i>
                <div class="search-result-info">
                    <div class="search-result-name">
                        ${student.full_name}
                        ${student.is_elder ? '<span class="badge-elder">Староста</span>' : ''}
                    </div>
                    <div class="search-result-path">${student.path}</div>
                </div>
            </div>
        `;
    });
    
    resultsHtml += '</div>';
    
    // Удаляем старые результаты
    const oldResults = document.querySelector('.search-results');
    if (oldResults) oldResults.remove();
    
    // Добавляем новые
    document.querySelector('.search-box').appendChild(createElementFromHTML(resultsHtml));
}

// ========== КОРЗИНА И UNDO/REDO ==========
let lastActions = [];

function undoLastAction() {
    if (lastActions.length === 0) {
        showNotification('Нет действий для отмены', 'info');
        return;
    }
    const lastAction = lastActions.pop();
    // TODO: реализовать отмену
    showNotification('Отмена последнего действия', 'info');
}

function redoLastAction() {
    showNotification('Повтор действия', 'info');
}

function openTrashModal() {
    const modal = document.getElementById('trashModal');
    const content = document.getElementById('trashContent');
    
    content.innerHTML = '<div class="text-center py-5"><div class="spinner-border"></div><p>Загрузка корзины...</p></div>';
    modal.style.display = 'block';
    
    fetch('/admin-panel/api/trash/')
        .then(response => response.json())
        .then(data => {
            if (data.items && data.items.length > 0) {
                let html = '<div class="list-group">';
                data.items.forEach(item => {
                    html += `
                        <div class="list-group-item">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <i class="bi bi-person-x"></i>
                                    <strong>${item.data.full_name || 'Без имени'}</strong>
                                    <small class="text-muted d-block">
                                        Удален: ${item.deleted_at} | Удалил: ${item.deleted_by}
                                    </small>
                                </div>
                                <button class="btn btn-sm btn-success" onclick="restoreItem(${item.id})">
                                    <i class="bi bi-arrow-return-left"></i> Восстановить
                                </button>
                            </div>
                        </div>
                    `;
                });
                html += '</div>';
                content.innerHTML = html;
            } else {
                content.innerHTML = '<div class="text-center py-5 text-muted">Корзина пуста</div>';
            }
        });
}

function restoreItem(cacheId) {
    fetch('/admin-panel/api/restore/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({cache_id: cacheId})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('✅ Элемент восстановлен', 'success');
            document.getElementById('trashModal').style.display = 'none';
            if (currentFolderType && currentFolderId) {
                loadFolderContent(currentFolderType, currentFolderId);
            }
        } else {
            showNotification('❌ Ошибка восстановления', 'danger');
        }
    });
}


// ==================== ЛОГИ ДЕЙСТВИЙ ====================

function toggleLogs() {
    const logsPanel = document.getElementById('logsPanel');
    
    if (logsPanel.style.display === 'none') {
        logsPanel.style.display = 'block';
        loadLogs();
    } else {
        logsPanel.style.display = 'none';
    }
}

function loadLogs() {
    fetch('/admin-panel/api/action-logs/')
        .then(response => response.json())
        .then(data => {
            let logsHtml = '<div class="logs-list">';
            
            data.logs.forEach(log => {
                let details = '';
                if (log.details) {
                    details = Object.entries(log.details)
                        .map(([k, v]) => `${k}: ${v}`)
                        .join(', ');
                }
                
                logsHtml += `
                    <div class="log-entry">
                        <div class="log-time">${log.time}</div>
                        <div class="log-user">👤 ${log.user}</div>
                        <div class="log-action">${log.action}</div>
                        <div class="log-model">${log.model}</div>
                        <div class="log-details">${details}</div>
                        <div class="log-ip">${log.ip}</div>
                    </div>
                `;
            });
            
            logsHtml += '</div>';
            document.getElementById('logsContent').innerHTML = logsHtml;
        });
}

// ==================== КЭШ И ВОССТАНОВЛЕНИЕ ====================

function clearCache() {
    if (confirm('🗑️ Очистить кэш? Восстановить удаленные элементы будет невозможно!')) {
        fetch('/admin-panel/api/clear-cache/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('✅ Кэш успешно очищен', 'success');
            }
        });
    }
}

// ==================== ДОПОЛНИТЕЛЬНЫЕ СТИЛИ ====================

const additionalStyles = `
    /* Стили для проводника */
    .folders-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 20px;
        padding: 20px;
    }
    
    .folder-item {
        position: relative;
        padding: 20px;
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .folder-item:hover {
        border-color: #0d6efd;
        box-shadow: 0 5px 15px rgba(13,110,253,0.1);
        transform: translateY(-2px);
    }
    
    .folder-icon i {
        font-size: 48px;
        color: #0d6efd;
        margin-bottom: 10px;
    }
    
    .folder-name {
        font-weight: 500;
        margin-bottom: 10px;
        word-break: break-word;
    }
    
    .folder-actions {
        position: absolute;
        top: 10px;
        right: 10px;
        display: flex;
        gap: 5px;
        opacity: 0;
        transition: opacity 0.2s;
    }
    
    .folder-item:hover .folder-actions {
        opacity: 1;
    }
    
    .folder-btn {
        width: 30px;
        height: 30px;
        border: none;
        background: white;
        border-radius: 4px;
        color: #6c757d;
        transition: all 0.2s;
    }
    
    .folder-btn:hover {
        background: #e9ecef;
        color: #0d6efd;
    }
    
    /* Стили для студентов */
    .students-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 15px;
        padding: 20px;
    }
    
    .student-card {
        display: flex;
        align-items: center;
        padding: 15px;
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        transition: all 0.2s;
    }
    
    .student-card:hover {
        border-color: #0d6efd;
        box-shadow: 0 2px 8px rgba(13,110,253,0.1);
    }
    
    .student-number {
        width: 30px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #e9ecef;
        border-radius: 50%;
        font-size: 12px;
        font-weight: 600;
        margin-right: 10px;
    }
    
    .student-avatar i {
        font-size: 40px;
        color: #6c757d;
        margin-right: 15px;
    }
    
    .student-info {
        flex: 1;
    }
    
    .student-name {
        font-weight: 600;
        margin-bottom: 5px;
    }
    
    .student-details {
        font-size: 12px;
        color: #6c757d;
    }
    
    .student-details span {
        display: inline-block;
        margin-right: 10px;
    }
    
    /* Поиск */
    .search-box {
        position: relative;
        width: 300px;
    }
    
    .search-box input {
        width: 100%;
        padding: 8px 12px 8px 35px;
        border: 1px solid #dee2e6;
        border-radius: 20px;
    }
    
    .search-box i {
        position: absolute;
        left: 12px;
        top: 50%;
        transform: translateY(-50%);
        color: #6c757d;
    }
    
    .search-results {
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        max-height: 400px;
        overflow-y: auto;
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        z-index: 1000;
    }
    
    /* Логи */
    .logs-panel {
        position: fixed;
        bottom: 0;
        right: 20px;
        width: 600px;
        height: 400px;
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 8px 8px 0 0;
        box-shadow: 0 -5px 20px rgba(0,0,0,0.1);
        z-index: 1050;
    }
    
    .logs-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 15px;
        background: #f8f9fa;
        border-bottom: 1px solid #dee2e6;
        border-radius: 8px 8px 0 0;
    }
    
    .logs-content {
        padding: 15px;
        overflow-y: auto;
        height: calc(100% - 60px);
    }
    
    .log-entry {
        padding: 10px;
        border-bottom: 1px solid #dee2e6;
        font-size: 13px;
    }
    
    .log-entry:hover {
        background: #f8f9fa;
    }
`;

// Добавляем стили в документ
const styleSheet = document.createElement("style");
styleSheet.textContent = additionalStyles;
document.head.appendChild(styleSheet);