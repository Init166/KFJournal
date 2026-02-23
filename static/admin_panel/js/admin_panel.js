// static/admin_panel/js/admin_panel.js

// ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================
let currentSelectedItem = null;
let sortableInstances = [];
let navigationStack = [];
let currentPosition = -1;
let currentFolderType = null;
let currentFolderId = null;
let currentItemToDelete = null;
let searchTimeout = null;

// ==================== ИНИЦИАЛИЗАЦИЯ ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Admin panel initialized');
    initDatabaseTree();
    initDragAndDrop();
    initSearch();
    loadNavigationHistory();
    
    // Восстанавливаем состояние из localStorage
    restoreExpandedState();
});

// ==================== ДЕРЕВО БАЗ ДАННЫХ ====================

function initDatabaseTree() {
    const treeItems = document.querySelectorAll('.tree-item-header');
    treeItems.forEach(header => {
        header.addEventListener('click', function(e) {
            // Если клик по кнопке раскрытия, не обрабатываем как выбор
            if (e.target.classList.contains('tree-toggle')) {
                toggleTreeItem(this);
                return;
            }
            
            // Иначе выбираем элемент
            const treeItem = this.closest('.tree-item');
            if (treeItem) {
                selectDatabaseItem(this, treeItem.dataset.type, treeItem.dataset.id);
            }
        });
    });
}

function toggleTreeItem(element) {
    const treeItem = element.closest('.tree-item');
    const children = treeItem.querySelector('.tree-children');
    const toggle = treeItem.querySelector('.tree-toggle');
    
    if (children) {
        if (children.style.display === 'none' || !children.style.display) {
            children.style.display = 'block';
            toggle.classList.add('expanded');
            saveExpandedState(treeItem.dataset.id, true);
        } else {
            children.style.display = 'none';
            toggle.classList.remove('expanded');
            saveExpandedState(treeItem.dataset.id, false);
        }
    }
}

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

function restoreExpandedState() {
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

// ==================== ЗАГРУЗКА КОНТЕНТА ====================

function loadDatabaseContent(type, id) {
    const contentContainer = document.getElementById('contentContainer');
    const contentTitle = document.getElementById('selectedItemTitle');
    const contentPath = document.getElementById('selectedItemPath');
    const contentActions = document.getElementById('contentActions');
    
    // Показываем загрузку
    contentContainer.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div><p class="mt-3">Загрузка данных...</p></div>';
    
    fetch(`/admin-panel/api/folder-content/?type=${type}&id=${id}`)
        .then(response => {
            if (!response.ok) throw new Error('Ошибка сети');
            return response.json();
        })
        .then(data => {
            // Обновляем заголовок и путь
            contentTitle.textContent = data.title || 'Без названия';
            contentPath.textContent = formatPath(data.path || []);
            
            // Добавляем в историю навигации
            addToHistory(type, id, data.title);
            
            // Обновляем кнопки действий
            updateActionButtons(type, data);
            
            // Рендерим контент
            renderContent(type, data, contentContainer);
        })
        .catch(error => {
            console.error('Error:', error);
            contentContainer.innerHTML = '<div class="alert alert-danger">Ошибка загрузки данных</div>';
        });
}

function formatPath(path) {
    if (!path || path.length === 0) return 'Главная';
    return path.map(p => p.name).join(' → ');
}

function updateActionButtons(type, data) {
    const actions = document.getElementById('contentActions');
    if (!actions) return;
    
    let buttons = '';
    
    if (type === 'group') {
        buttons = `
            <button class="action-btn action-btn-success" onclick="openCreateModal('student', ${data.id})">
                <i class="bi bi-person-plus"></i> Добавить студента
            </button>
            <button class="action-btn action-btn-outline" onclick="openPasswordManager()">
                <i class="bi bi-key"></i> Пароли
            </button>
        `;
    } else {
        buttons = `
            <button class="action-btn action-btn-success" onclick="openCreateModal('${type}', ${data.id})">
                <i class="bi bi-plus-circle"></i> Создать
            </button>
        `;
    }
    
    actions.innerHTML = buttons;
}

function renderContent(type, data, container) {
    if (type === 'group' && data.items) {
        renderStudentsGrid(data.items, container);
    } else if (data.items) {
        renderFoldersGrid(data.items, type, container);
    } else {
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-folder2-open display-1 text-muted"></i>
                <h3 class="mt-3">Папка пуста</h3>
                <p class="text-muted">Нажмите "Создать" чтобы добавить новый элемент</p>
            </div>
        `;
    }
}

function renderFoldersGrid(items, parentType, container) {
    if (!items || items.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-folder2-open display-1 text-muted"></i>
                <h3 class="mt-3">Папка пуста</h3>
                <p class="text-muted">Нажмите "Создать" чтобы добавить новый элемент</p>
            </div>
        `;
        return;
    }
    
    let html = '<div class="folders-grid">';
    
    items.forEach(item => {
        html += `
            <div class="folder-item" ondblclick="navigateTo('${item.type}', ${item.id}, '${item.name}')">
                <div class="folder-icon">
                    <i class="bi ${getFolderIcon(item.type)}"></i>
                </div>
                <div class="folder-name">${item.name}</div>
                <div class="folder-actions">
                    <button class="folder-btn" onclick="event.stopPropagation(); renameFolder('${item.type}', ${item.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="folder-btn" onclick="event.stopPropagation(); openDeleteModal('${item.type}', ${item.id}, '${item.name}')">
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

function getFolderIcon(type) {
    const icons = {
        'level': 'bi-database-fill',
        'form': 'bi-folder-fill',
        'course': 'bi-layers-fill',
        'group': 'bi-people-fill',
        'student': 'bi-person-circle'
    };
    return icons[type] || 'bi-folder';
}

function renderStudentsGrid(students, container) {
    if (!students || students.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-people display-1 text-muted"></i>
                <h3 class="mt-3">В группе нет студентов</h3>
                <p class="text-muted">Нажмите "Добавить студента" чтобы создать первую запись</p>
                <button class="btn btn-primary mt-3" onclick="openCreateModal('student', ${currentFolderId})">
                    <i class="bi bi-person-plus"></i> Добавить студента
                </button>
            </div>
        `;
        return;
    }
    
    // Сортируем студентов по ФИО
    const sortedStudents = [...students].sort((a, b) => 
        (a.full_name || '').localeCompare(b.full_name || '', 'ru')
    );
    
    let html = `
        <div class="d-flex justify-content-between align-items-center mb-3">
            <span class="badge bg-primary">Всего студентов: ${sortedStudents.length}</span>
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
                        <th style="width: 50px">#</th>
                        <th style="width: 40px"></th>
                        <th>ФИО</th>
                        <th>Логин</th>
                        <th>Email</th>
                        <th>Статус</th>
                        <th>Действия</th>
                    </tr>
                </thead>
                <tbody id="studentTableBody">
    `;
    
    sortedStudents.forEach((student, index) => {
        html += `
            <tr draggable="true" ondragstart="dragStart(event, 'student', ${student.id})" 
                data-id="${student.id}" data-type="student" data-name="${student.full_name}">
                <td><span class="badge bg-light text-dark">${index + 1}</span></td>
                <td><i class="bi bi-grip-vertical text-muted" style="cursor: move;"></i></td>
                <td>
                    <div class="d-flex align-items-center">
                        <i class="bi bi-person-circle me-2 text-primary"></i>
                        ${student.full_name || 'Без имени'}
                        ${student.is_elder ? '<span class="badge-elder ms-2">Староста ⭐</span>' : ''}
                    </div>
                </td>
                <td><code>${student.login || ''}</code></td>
                <td>${student.email || '<span class="text-muted">—</span>'}</td>
                <td>
                    <span class="badge ${student.is_active ? 'bg-success' : 'bg-secondary'}">
                        ${student.is_active ? 'Активен' : 'Неактивен'}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="openEditModal('student', ${student.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="openDeleteModal('student', ${student.id}, '${student.full_name}')">
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
    initStudentDragAndDrop();
}

// ==================== НАВИГАЦИЯ ====================

function navigateTo(type, id, title) {
    // Обрезаем стек если мы не в конце
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
    loadDatabaseContent(type, id);
    
    // Обновляем кнопки навигации
    updateNavigationButtons();
}

function addToHistory(type, id, title) {
    if (currentPosition < navigationStack.length - 1) {
        navigationStack = navigationStack.slice(0, currentPosition + 1);
    }
    
    navigationStack.push({ type, id, title });
    currentPosition = navigationStack.length - 1;
    updateNavigationButtons();
}

function goBack() {
    if (currentPosition > 0) {
        currentPosition--;
        const item = navigationStack[currentPosition];
        loadDatabaseContent(item.type, item.id);
        updateNavigationButtons();
        expandTreeItem(item.type, item.id);
    }
}

function goForward() {
    if (currentPosition < navigationStack.length - 1) {
        currentPosition++;
        const item = navigationStack[currentPosition];
        loadDatabaseContent(item.type, item.id);
        updateNavigationButtons();
        expandTreeItem(item.type, item.id);
    }
}

function goUp() {
    if (currentFolderType && currentFolderId) {
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
    const backBtn = document.getElementById('backBtn');
    const forwardBtn = document.getElementById('forwardBtn');
    const upBtn = document.getElementById('upBtn');
    
    if (backBtn) backBtn.disabled = currentPosition <= 0;
    if (forwardBtn) forwardBtn.disabled = currentPosition >= navigationStack.length - 1;
    if (upBtn) upBtn.disabled = !currentFolderType || !currentFolderId;
}

function expandTreeItem(type, id) {
    const treeItem = document.querySelector(`.tree-item[data-id="${id}"][data-type="${type}"]`);
    if (!treeItem) return;
    
    // Раскрываем родительские папки
    let parent = treeItem.closest('.tree-children');
    while (parent) {
        parent.style.display = 'block';
        const toggle = parent.closest('.tree-item')?.querySelector('.tree-toggle');
        if (toggle) toggle.classList.add('expanded');
        parent = parent.parentElement?.closest('.tree-children');
    }
    
    // Подсвечиваем текущий элемент
    document.querySelectorAll('.tree-item-header.active').forEach(el => {
        el.classList.remove('active');
    });
    
    const header = treeItem.querySelector('.tree-item-header');
    if (header) header.classList.add('active');
}

// ==================== ПОИСК ====================

function initSearch() {
    const searchInput = document.getElementById('searchQuery');
    if (!searchInput) return;
    
    searchInput.addEventListener('input', function(e) {
        clearTimeout(searchTimeout);
        
        const query = e.target.value.trim();
        
        if (query.length < 2) {
            document.getElementById('searchResultsContainer').innerHTML = '';
            return;
        }
        
        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 300);
    });
}

function openSearchModal() {
    const modal = document.getElementById('searchModal');
    if (modal) {
        modal.style.display = 'block';
        document.getElementById('searchQuery').focus();
    }
}

function closeSearchModal() {
    document.getElementById('searchModal').style.display = 'none';
}

function performSearch(query) {
    const resultsContainer = document.getElementById('searchResultsContainer');
    resultsContainer.innerHTML = '<div class="text-center py-4"><div class="spinner-border"></div><p>Поиск...</p></div>';
    
    fetch(`/admin-panel/api/search/?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            if (data.results && data.results.length > 0) {
                let html = `<div class="mb-2">Найдено: <strong>${data.count}</strong></div>`;
                
                data.results.forEach(student => {
                    html += `
                        <div class="search-result-item" onclick="navigateToStudent(${student.id})">
                            <i class="bi bi-person-circle fs-4"></i>
                            <div class="search-result-info">
                                <div class="search-result-name">
                                    ${student.full_name}
                                    ${student.is_elder ? '<span class="badge-elder ms-2">Староста</span>' : ''}
                                </div>
                                <div class="search-result-details">
                                    <span><i class="bi bi-box-arrow-in-right"></i> ${student.login}</span>
                                    ${student.email ? `<span><i class="bi bi-envelope"></i> ${student.email}</span>` : ''}
                                </div>
                                <div class="search-result-path">
                                    <i class="bi bi-folder"></i> ${student.path || 'Нет группы'}
                                </div>
                            </div>
                        </div>
                    `;
                });
                
                resultsContainer.innerHTML = html;
            } else {
                resultsContainer.innerHTML = '<div class="text-center text-muted py-4">Ничего не найдено</div>';
            }
        })
        .catch(error => {
            resultsContainer.innerHTML = '<div class="alert alert-danger">Ошибка поиска</div>';
        });
}

function navigateToStudent(studentId) {
    closeSearchModal();
    // TODO: Реализовать переход к студенту
    alert('Переход к студенту будет доступен в следующей версии');
}

// ==================== DRAG & DROP ====================

function initDragAndDrop() {
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
            if (!draggedData) return;
            
            const [draggedType, draggedId] = draggedData.split(':');
            const targetItem = target.closest('[data-type]');
            if (!targetItem) return;
            
            const targetType = targetItem.dataset.type;
            const targetId = targetItem.dataset.id;
            
            moveItem(draggedType, draggedId, targetType, targetId);
        });
    });
}

function initStudentDragAndDrop() {
    const tbody = document.getElementById('studentTableBody');
    if (!tbody) return;
    
    // Очищаем предыдущие экземпляры Sortable
    sortableInstances.forEach(instance => instance.destroy());
    sortableInstances = [];
    
    const sortable = Sortable.create(tbody, {
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
            
            if (evt.to.id !== evt.from.id) {
                showNotification(
                    `🎓 Студент ${studentName} перемещен. Выберите целевую группу в левой панели и нажмите Ctrl+V`,
                    'info'
                );
            }
        }
    });
    
    sortableInstances.push(sortable);
}

function dragStart(event, type, id) {
    event.dataTransfer.setData('text/plain', `${type}:${id}`);
    event.dataTransfer.effectAllowed = 'move';
    event.target.closest('tr')?.classList.add('dragging');
}

function dragEnd(event) {
    event.target.closest('tr')?.classList.remove('dragging');
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
            if (currentFolderType && currentFolderId) {
                loadDatabaseContent(currentFolderType, currentFolderId);
            }
        } else {
            showNotification('❌ Ошибка при перемещении: ' + data.error, 'danger');
        }
    });
}

// ==================== МОДАЛЬНЫЕ ОКНА ====================

function openCreateModal(type, parentId = null) {
    const modal = document.getElementById('itemModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    
    modalTitle.textContent = `Создание ${getTypeName(type)}`;
    modalBody.innerHTML = generateCreateForm(type, parentId);
    modal.style.display = 'block';
    hideAddMenu();
}

function openEditModal(type, id) {
    const modal = document.getElementById('itemModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    
    modalTitle.textContent = `Редактирование ${getTypeName(type)}`;
    modalBody.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div><p class="mt-3">Загрузка данных...</p></div>';
    modal.style.display = 'block';
    
    // ИСПРАВЛЕНО: используем folder-content вместо content
    const url = type === 'student' 
        ? `/admin-panel/api/student/${id}/`
        : `/admin-panel/api/folder-content/?type=${type}&id=${id}`;
    
    fetch(url)
        .then(response => {
            if (!response.ok) throw new Error('Ошибка сети');
            return response.json();
        })
        .then(data => {
            modalBody.innerHTML = generateEditForm(type, data);
        })
        .catch(error => {
            console.error('Ошибка:', error);
            modalBody.innerHTML = `
                <div class="text-center py-4">
                    <i class="bi bi-exclamation-triangle-fill text-danger display-4"></i>
                    <h4 class="mt-3 text-danger">Ошибка загрузки данных</h4>
                    <p class="text-muted">Не удалось загрузить информацию</p>
                    <button class="btn btn-primary mt-3" onclick="closeModal()">Закрыть</button>
                </div>
            `;
        });
}

function openDeleteModal(type, id, name) {
    const modal = document.getElementById('deleteModal');
    const deleteMessage = document.getElementById('deleteMessage');
    currentItemToDelete = { type, id };
    deleteMessage.textContent = `Вы действительно хотите удалить ${getTypeName(type)} "${name || ''}"? Это действие нельзя отменить!`;
    modal.style.display = 'block';
}

function closeModal() {
    document.getElementById('itemModal').style.display = 'none';
}

function closeDeleteModal() {
    document.getElementById('deleteModal').style.display = 'none';
    currentItemToDelete = null;
}

function confirmDelete() {
    if (!currentItemToDelete) return;
    
    const deleteBtn = document.querySelector('#deleteModal .action-btn-danger');
    const originalText = deleteBtn.innerHTML;
    deleteBtn.innerHTML = '<i class="bi bi-arrow-repeat"></i> Удаление...';
    deleteBtn.disabled = true;
    
    fetch('/admin-panel/api/delete/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(currentItemToDelete)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            closeDeleteModal();
            if (currentFolderType && currentFolderId) {
                loadDatabaseContent(currentFolderType, currentFolderId);
            }
            showNotification('✅ Элемент успешно удален', 'success');
        } else {
            showNotification('❌ Ошибка при удалении: ' + (data.error || 'Неизвестная ошибка'), 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('❌ Ошибка сети при удалении', 'danger');
    })
    .finally(() => {
        deleteBtn.innerHTML = originalText;
        deleteBtn.disabled = false;
    });
}

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

// ==================== ФОРМЫ ====================

function generateCreateForm(type, parentId) {
    switch(type) {
        case 'student':
            return `
                <form id="createForm" onsubmit="submitCreateForm(event, 'student', ${parentId})">
                    <div class="form-group">
                        <label>👤 ФИО студента</label>
                        <input type="text" class="form-control" name="full_name" required 
                               placeholder="Иванов Иван Иванович" id="studentFullName">
                    </div>
                    <div class="form-group">
                        <label>🔐 Логин</label>
                        <input type="text" class="form-control" name="login" required 
                               placeholder="ivanov.ii" id="studentLogin">
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
                            Пароль будет сгенерирован автоматически
                        </small>
                    </div>
                    <button type="submit" class="action-btn action-btn-primary w-100">
                        <i class="bi bi-person-plus"></i> Создать
                    </button>
                </form>
                <script>
                    document.getElementById('studentFullName')?.addEventListener('input', function(e) {
                        const name = e.target.value;
                        const loginInput = document.getElementById('studentLogin');
                        if (name && !loginInput.value) {
                            const translit = {
                                'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e',
                                'ё':'e','ж':'zh','з':'z','и':'i','й':'y','к':'k',
                                'л':'l','м':'m','н':'n','о':'o','п':'p','р':'r',
                                'с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'ts',
                                'ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'',
                                'э':'e','ю':'yu','я':'ya'
                            };
                            let login = name.toLowerCase()
                                .split(' ')
                                .map((part, i) => {
                                    let trans = '';
                                    for (let char of part) {
                                        trans += translit[char] || char;
                                    }
                                    return i === 0 ? trans : trans[0];
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
                    </div>
                    <button type="submit" class="action-btn action-btn-primary w-100">
                        <i class="bi bi-database-add"></i> Создать
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
                        <i class="bi bi-folder-plus"></i> Создать
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
                        <i class="bi bi-layers"></i> Создать
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
                        <i class="bi bi-people"></i> Создать
                    </button>
                </form>
            `;
            
        default:
            return '<p class="text-center text-muted py-4">Форма для данного типа находится в разработке</p>';
    }
}

function generateEditForm(type, data) {
    if (type === 'student') {
        const isElder = data.user_type === 'elder' || data.is_elder;
        
        return `
            <form id="editForm" onsubmit="submitEditForm(event, 'student', ${data.id})">
                <div class="form-group">
                    <label>👤 ФИО</label>
                    <input type="text" class="form-control" name="full_name" 
                           value="${escapeHtml(data.full_name || '')}" required>
                </div>
                
                <div class="form-group">
                    <label>🔐 Логин</label>
                    <input type="text" class="form-control" name="login" 
                           value="${escapeHtml(data.login || '')}" required>
                </div>
                
                <div class="form-group">
                    <label>🔑 Пароль</label>
                    <div class="input-group">
                        <input type="text" class="form-control" name="password" 
                               id="password-${data.id}" value="${escapeHtml(data.password || '')}">
                        <button class="btn btn-outline-secondary" type="button" 
                                onclick="togglePasswordVisibility(${data.id})">
                            <i class="bi bi-eye" id="eye-${data.id}"></i>
                        </button>
                    </div>
                </div>
                
                <div class="form-group">
                    <label>📧 Email</label>
                    <input type="email" class="form-control" name="email" 
                           value="${escapeHtml(data.email || '')}">
                </div>
                
                <div class="form-group">
                    <label>📱 Телефон</label>
                    <input type="tel" class="form-control" name="phone" 
                           value="${escapeHtml(data.phone || '')}">
                </div>
                
                <div class="form-group">
                    <label>👥 Тип пользователя</label>
                    <select class="form-control" name="user_type" id="user-type-${data.id}">
                        <option value="student" ${data.user_type === 'student' ? 'selected' : ''}>🎓 Студент</option>
                        <option value="elder" ${data.user_type === 'elder' ? 'selected' : ''}>⭐ Староста</option>
                        <option value="dean" ${data.user_type === 'dean' ? 'selected' : ''}>🏛️ Деканат</option>
                        <option value="department" ${data.user_type === 'department' ? 'selected' : ''}>📋 Отдел</option>
                        <option value="teacher" ${data.user_type === 'teacher' ? 'selected' : ''}>👨‍🏫 Преподаватель</option>
                        <option value="admin" ${data.user_type === 'admin' ? 'selected' : ''}>🛠️ Администратор</option>
                    </select>
                </div>
                
                <div class="form-check mb-3">
                    <input type="checkbox" class="form-check-input" name="is_active" id="isActive" 
                           ${data.is_active ? 'checked' : ''}>
                    <label class="form-check-label" for="isActive">✅ Активен</label>
                </div>
                
                <button type="submit" class="action-btn action-btn-primary w-100">
                    <i class="bi bi-check-circle"></i> Сохранить изменения
                </button>
            </form>
            
            <script>
                document.getElementById('user-type-${data.id}')?.addEventListener('change', function(e) {
                    // Здесь можно добавить логику для показа прав старосты
                });
            <\/script>
        `;
    }
    
    return '<p class="text-center text-muted py-4">Редактирование в разработке</p>';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function togglePasswordVisibility(studentId) {
    const passwordInput = document.getElementById(`password-${studentId}`);
    const eyeIcon = document.getElementById(`eye-${studentId}`);
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        eyeIcon.classList.remove('bi-eye');
        eyeIcon.classList.add('bi-eye-slash');
    } else {
        passwordInput.type = 'password';
        eyeIcon.classList.remove('bi-eye-slash');
        eyeIcon.classList.add('bi-eye');
    }
}

function submitCreateForm(event, type, parentId) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    data.type = type;
    
    if (parentId) {
        if (type === 'student') data.group_id = parentId;
        if (type === 'form') data.level_id = parentId;
        if (type === 'course') data.form_id = parentId;
        if (type === 'group') data.course_id = parentId;
    }
    
    fetch('/admin-panel/api/create/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            closeModal();
            if (currentFolderType && currentFolderId) {
                loadDatabaseContent(currentFolderType, currentFolderId);
            }
            showNotification('✅ Элемент успешно создан', 'success');
        } else {
            showNotification('❌ Ошибка: ' + data.error, 'danger');
        }
    });
}

function submitEditForm(event, type, id) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    
    data.type = type;
    data.id = id;
    
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="bi bi-arrow-repeat"></i> Сохранение...';
    submitBtn.disabled = true;
    
    fetch('/admin-panel/api/update/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (!response.ok) throw new Error('Ошибка сети');
        return response.json();
    })
    .then(data => {
        if (data.success) {
            closeModal();
            if (currentFolderType && currentFolderId) {
                loadDatabaseContent(currentFolderType, currentFolderId);
            }
            showNotification('✅ Изменения сохранены!', 'success');
        } else {
            showNotification('❌ Ошибка: ' + (data.error || 'Неизвестная ошибка'), 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('❌ Ошибка при сохранении', 'danger');
    })
    .finally(() => {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
}

// ==================== ПЕРЕИМЕНОВАНИЕ ====================

function renameFolder(type, id) {
    const folderItem = event.target.closest('.folder-item');
    const folderName = folderItem.querySelector('.folder-name');
    const oldName = folderName.textContent.trim();
    
    const input = document.createElement('input');
    input.type = 'text';
    input.value = oldName;
    input.className = 'form-control form-control-sm';
    input.style.width = '100%';
    
    folderName.innerHTML = '';
    folderName.appendChild(input);
    input.focus();
    
    input.addEventListener('blur', () => {
        saveRename(type, id, input.value, folderName, oldName);
    });
    
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            saveRename(type, id, input.value, folderName, oldName);
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
            showNotification(`✅ Переименовано в "${newName}"`, 'success');
            
            if (currentFolderType && currentFolderId) {
                loadDatabaseContent(currentFolderType, currentFolderId);
            }
        } else {
            element.innerHTML = oldName;
            showNotification('❌ Ошибка при переименовании', 'danger');
        }
    });
}

// ==================== ПАРОЛИ ====================

function openPasswordManager() {
    const modal = document.getElementById('passwordModal');
    const content = document.getElementById('passwordContent');
    
    content.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div><p>Загрузка паролей...</p></div>';
    modal.style.display = 'block';
    
    fetch('/admin-panel/api/passwords/')
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            if (data.error) {
                content.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                return;
            }
            
            if (data.passwords && data.passwords.length > 0) {
                let html = `
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead class="table-light">
                                <tr>
                                    <th>ID</th>
                                    <th>ФИО</th>
                                    <th>Логин</th>
                                    <th>Пароль</th>
                                    <th>Тип</th>
                                    <th>Группа</th>
                                </tr>
                            </thead>
                            <tbody>
                `;
                
                data.passwords.forEach(user => {
                    html += `
                        <tr>
                            <td>${user.id}</td>
                            <td>${escapeHtml(user.full_name)}</td>
                            <td><code>${escapeHtml(user.login)}</code></td>
                            <td>
                                <span class="password-field" id="pass-${user.id}">
                                    ••••••••
                                </span>
                                <button class="btn btn-sm btn-link" onclick="togglePassword(${user.id}, '${escapeHtml(user.password)}')">
                                    <i class="bi bi-eye"></i>
                                </button>
                            </td>
                            <td><span class="badge bg-info">${escapeHtml(user.user_type)}</span></td>
                            <td>${escapeHtml(user.group)}</td>
                        </tr>
                    `;
                });
                
                html += `
                            </tbody>
                        </table>
                    </div>
                `;
                content.innerHTML = html;
            } else {
                content.innerHTML = '<div class="alert alert-info">Нет пользователей</div>';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            content.innerHTML = `<div class="alert alert-danger">Ошибка загрузки: ${error.message}</div>`;
        });
}

function togglePassword(userId, password) {
    const field = document.getElementById(`pass-${userId}`);
    if (field.textContent === '••••••••') {
        field.textContent = password;
    } else {
        field.textContent = '••••••••';
    }
}

// ==================== ЛОГИ ====================

function toggleLogs() {
    const panel = document.getElementById('logsPanel');
    if (!panel) return;
    
    if (panel.style.display === 'none') {
        panel.style.display = 'block';
        loadLogs();
    } else {
        panel.style.display = 'none';
    }
}

function loadLogs() {
    const container = document.getElementById('logsContent');
    if (!container) return;
    
    fetch('/admin-panel/api/action-logs/')
        .then(response => response.json())
        .then(data => {
            let html = '<div class="logs-list">';
            
            (data.logs || []).forEach(log => {
                html += `
                    <div class="log-entry">
                        <small class="text-muted">${log.time}</small>
                        <div><strong>${log.user}</strong> ${log.action}</div>
                        <div class="text-muted">${log.model}</div>
                    </div>
                `;
            });
            
            html += '</div>';
            container.innerHTML = html;
        })
        .catch(error => {
            container.innerHTML = '<div class="alert alert-danger">Ошибка загрузки логов</div>';
        });
}

// ==================== МЕНЮ ДОБАВЛЕНИЯ ====================

function showAddMenu() {
    const menu = document.getElementById('addMenu');
    const button = document.querySelector('.add-database-btn');
    
    if (!menu) return;
    
    menu.style.display = 'block';
    
    if (button) {
        const rect = button.getBoundingClientRect();
        menu.style.top = (rect.bottom + window.scrollY + 5) + 'px';
        menu.style.left = (rect.left + window.scrollX) + 'px';
    }
    
    setTimeout(() => {
        document.addEventListener('click', hideAddMenuOnClickOutside);
    }, 10);
}

function hideAddMenu() {
    const menu = document.getElementById('addMenu');
    if (menu) menu.style.display = 'none';
    document.removeEventListener('click', hideAddMenuOnClickOutside);
}

function hideAddMenuOnClickOutside(event) {
    const menu = document.getElementById('addMenu');
    const button = document.querySelector('.add-database-btn');
    
    if (menu && button && !menu.contains(event.target) && !button.contains(event.target)) {
        hideAddMenu();
    }
}

// ==================== ИСТОРИЯ НАВИГАЦИИ ====================

function loadNavigationHistory() {
    fetch('/admin-panel/api/navigation-history/')
        .then(response => response.json())
        .then(data => {
            if (data.history) {
                navigationStack = data.history;
                currentPosition = navigationStack.length - 1;
                updateNavigationButtons();
            }
        })
        .catch(error => console.error('Error loading navigation history:', error));
}

// ==================== УТИЛИТЫ ====================

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

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} position-fixed top-0 end-0 m-3`;
    notification.style.zIndex = '9999';
    notification.style.minWidth = '200px';
    notification.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
    notification.innerHTML = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transition = 'opacity 0.3s';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ==================== ЭКСПОРТ/ИМПОРТ ====================

function exportGroup(groupId) {
    alert('Экспорт данных будет доступен в следующей версии');
}

function importExcel() {
    alert('Импорт из Excel будет доступен в следующей версии');
}

function clearCache() {
    if (confirm('🗑️ Очистить кэш? Это действие нельзя отменить!')) {
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
            } else {
                showNotification('❌ Ошибка при очистке кэша', 'danger');
            }
        });
    }
}

function sortStudents(criteria) {
    // TODO: Реализовать сортировку
    showNotification('Сортировка будет доступна в следующей версии', 'info');
}