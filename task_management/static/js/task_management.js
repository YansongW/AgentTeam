/**
 * 任务管理模块JavaScript
 */
document.addEventListener('DOMContentLoaded', function() {
    // 初始化变量
    const API_BASE_URL = '/api/tasks';
    let currentPage = 1;
    let pageSize = 10;
    let totalPages = 0;
    let selectedTasks = new Set();
    let tasks = [];
    
    // DOM元素
    const taskTableBody = document.getElementById('taskTableBody');
    const taskPagination = document.getElementById('taskPagination');
    const filterForm = document.getElementById('filterForm');
    const resetFilterBtn = document.getElementById('resetFilterBtn');
    const selectAllTasks = document.getElementById('selectAllTasks');
    const createTaskBtn = document.getElementById('createTaskBtn');
    const taskModal = new bootstrap.Modal(document.getElementById('taskModal'));
    const assignTaskModal = new bootstrap.Modal(document.getElementById('assignTaskModal'));
    const taskForm = document.getElementById('taskForm');
    const assignTaskForm = document.getElementById('assignTaskForm');
    const saveTaskBtn = document.getElementById('saveTaskBtn');
    const saveAssignBtn = document.getElementById('saveAssignBtn');
    const assignSelectedBtn = document.getElementById('assignSelectedBtn');
    const taskProgress = document.getElementById('taskProgress');
    const progressValue = document.getElementById('progressValue');
    const assignToUser = document.getElementById('assignToUser');
    const assignToAgent = document.getElementById('assignToAgent');
    const userSelectContainer = document.getElementById('userSelectContainer');
    const agentSelectContainer = document.getElementById('agentSelectContainer');
    
    // 初始化
    loadTasks();
    loadGroups();
    loadUsers();
    loadAgents();
    loadParentTasks();
    
    // 事件监听器
    filterForm.addEventListener('submit', function(e) {
        e.preventDefault();
        currentPage = 1;
        loadTasks();
    });
    
    resetFilterBtn.addEventListener('click', function() {
        filterForm.reset();
        currentPage = 1;
        loadTasks();
    });
    
    selectAllTasks.addEventListener('change', function() {
        const checkboxes = taskTableBody.querySelectorAll('.task-checkbox');
        checkboxes.forEach(checkbox => {
            checkbox.checked = selectAllTasks.checked;
            if (selectAllTasks.checked) {
                selectedTasks.add(checkbox.value);
                checkbox.closest('tr').classList.add('selected');
            } else {
                selectedTasks.delete(checkbox.value);
                checkbox.closest('tr').classList.remove('selected');
            }
        });
        updateBulkActionState();
    });
    
    createTaskBtn.addEventListener('click', function() {
        resetTaskForm();
        document.getElementById('taskModalLabel').textContent = '创建任务';
        taskModal.show();
    });
    
    saveTaskBtn.addEventListener('click', function() {
        saveTask();
    });
    
    saveAssignBtn.addEventListener('click', function() {
        assignTask();
    });
    
    assignSelectedBtn.addEventListener('click', function() {
        if (selectedTasks.size === 0) return;
        openAssignModal();
    });
    
    taskProgress.addEventListener('input', function() {
        progressValue.textContent = taskProgress.value;
    });
    
    // 切换分配给用户或代理
    assignToUser.addEventListener('change', function() {
        userSelectContainer.classList.remove('d-none');
        agentSelectContainer.classList.add('d-none');
    });
    
    assignToAgent.addEventListener('change', function() {
        userSelectContainer.classList.add('d-none');
        agentSelectContainer.classList.remove('d-none');
    });
    
    // 批量操作处理
    document.querySelectorAll('.bulk-action').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const action = this.dataset.action;
            const value = this.dataset.value;
            
            if (selectedTasks.size === 0) return;
            
            performBulkAction(action, value);
        });
    });
    
    // 加载任务列表
    function loadTasks() {
        const formData = new FormData(filterForm);
        const searchParams = new URLSearchParams();
        
        // 将表单数据转换为URL参数
        for (const [key, value] of formData.entries()) {
            if (value) searchParams.append(key, value);
        }
        
        // 添加分页参数
        searchParams.append('page', currentPage);
        searchParams.append('page_size', pageSize);
        
        // 清空选择
        selectedTasks.clear();
        selectAllTasks.checked = false;
        
        // 显示加载中
        taskTableBody.innerHTML = '<tr><td colspan="8" class="text-center py-4">加载中...</td></tr>';
        
        // 获取任务数据
        fetch(`${API_BASE_URL}/tasks/?${searchParams.toString()}`)
            .then(response => {
                if (!response.ok) throw new Error('网络响应异常');
                return response.json();
            })
            .then(data => {
                tasks = data.results;
                totalPages = Math.ceil(data.count / pageSize);
                
                if (tasks.length === 0) {
                    taskTableBody.innerHTML = '<tr><td colspan="8" class="text-center py-4">暂无任务</td></tr>';
                    taskPagination.innerHTML = '';
                    return;
                }
                
                // 渲染任务列表
                renderTasks(tasks);
                
                // 渲染分页
                renderPagination(currentPage, totalPages);
            })
            .catch(error => {
                console.error('获取任务失败:', error);
                taskTableBody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-danger">获取任务失败，请刷新重试</td></tr>';
            });
    }
    
    // 渲染任务列表
    function renderTasks(tasks) {
        taskTableBody.innerHTML = '';
        
        tasks.forEach(task => {
            const tr = document.createElement('tr');
            tr.className = 'task-item';
            tr.dataset.id = task.id;
            
            // 格式化截止日期
            let dueDateDisplay = '无';
            let dueDateClass = '';
            
            if (task.due_date) {
                const dueDate = new Date(task.due_date);
                const now = new Date();
                const diffDays = Math.floor((dueDate - now) / (1000 * 60 * 60 * 24));
                
                dueDateDisplay = dueDate.toLocaleDateString();
                
                if (diffDays < 0) {
                    dueDateClass = 'overdue';
                } else if (diffDays < 3) {
                    dueDateClass = 'approaching';
                }
            }
            
            tr.innerHTML = `
                <td>
                    <input type="checkbox" class="form-check-input task-checkbox" value="${task.id}">
                </td>
                <td>
                    <a href="#" class="task-title" data-id="${task.id}">${task.title}</a>
                    ${task.description ? '<small class="text-muted d-block text-truncate" style="max-width: 250px;">' + task.description.substring(0, 100) + '</small>' : ''}
                </td>
                <td>
                    <span class="status-badge status-${task.status}">${getStatusText(task.status)}</span>
                </td>
                <td>
                    <span class="priority-badge priority-${task.priority}">${getPriorityText(task.priority)}</span>
                </td>
                <td>
                    <span class="due-date ${dueDateClass}">${dueDateDisplay}</span>
                </td>
                <td>
                    <div class="progress">
                        <div class="progress-bar" role="progressbar" style="width: ${task.progress}%;" 
                             aria-valuenow="${task.progress}" aria-valuemin="0" aria-valuemax="100"></div>
                    </div>
                    <small class="text-muted">${task.progress}%</small>
                </td>
                <td>
                    ${task.creator_name || '系统'}
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button type="button" class="btn btn-outline-primary edit-task" data-id="${task.id}">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button type="button" class="btn btn-outline-success assign-task" data-id="${task.id}">
                            <i class="fas fa-user-check"></i>
                        </button>
                        <button type="button" class="btn btn-outline-danger delete-task" data-id="${task.id}">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                </td>
            `;
            
            taskTableBody.appendChild(tr);
        });
        
        // 添加事件监听器
        addTaskEventListeners();
    }
    
    // 添加任务事件监听器
    function addTaskEventListeners() {
        // 任务选择
        taskTableBody.querySelectorAll('.task-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                const taskId = this.value;
                const row = this.closest('tr');
                
                if (this.checked) {
                    selectedTasks.add(taskId);
                    row.classList.add('selected');
                } else {
                    selectedTasks.delete(taskId);
                    row.classList.remove('selected');
                    selectAllTasks.checked = false;
                }
                
                updateBulkActionState();
            });
        });
        
        // 任务标题点击
        taskTableBody.querySelectorAll('.task-title').forEach(title => {
            title.addEventListener('click', function(e) {
                e.preventDefault();
                const taskId = this.dataset.id;
                editTask(taskId);
            });
        });
        
        // 编辑按钮
        taskTableBody.querySelectorAll('.edit-task').forEach(button => {
            button.addEventListener('click', function() {
                const taskId = this.dataset.id;
                editTask(taskId);
            });
        });
        
        // 分配按钮
        taskTableBody.querySelectorAll('.assign-task').forEach(button => {
            button.addEventListener('click', function() {
                const taskId = this.dataset.id;
                openAssignModal(taskId);
            });
        });
        
        // 删除按钮
        taskTableBody.querySelectorAll('.delete-task').forEach(button => {
            button.addEventListener('click', function() {
                const taskId = this.dataset.id;
                confirmDeleteTask(taskId);
            });
        });
    }
    
    // 渲染分页
    function renderPagination(currentPage, totalPages) {
        taskPagination.innerHTML = '';
        
        if (totalPages <= 1) return;
        
        // 上一页
        const prevLi = document.createElement('li');
        prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
        prevLi.innerHTML = `<a class="page-link" href="#" data-page="${currentPage - 1}">上一页</a>`;
        taskPagination.appendChild(prevLi);
        
        // 页码
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, startPage + 4);
        
        for (let i = startPage; i <= endPage; i++) {
            const pageLi = document.createElement('li');
            pageLi.className = `page-item ${i === currentPage ? 'active' : ''}`;
            pageLi.innerHTML = `<a class="page-link" href="#" data-page="${i}">${i}</a>`;
            taskPagination.appendChild(pageLi);
        }
        
        // 下一页
        const nextLi = document.createElement('li');
        nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
        nextLi.innerHTML = `<a class="page-link" href="#" data-page="${currentPage + 1}">下一页</a>`;
        taskPagination.appendChild(nextLi);
        
        // 添加分页事件
        taskPagination.querySelectorAll('.page-link').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                if (this.parentElement.classList.contains('disabled')) return;
                
                currentPage = parseInt(this.dataset.page);
                loadTasks();
            });
        });
    }
    
    // 加载群组选项
    function loadGroups() {
        fetch('/api/groups/groups/')
            .then(response => response.json())
            .then(data => {
                const groupFilter = document.getElementById('groupFilter');
                const taskGroup = document.getElementById('taskGroup');
                
                data.results.forEach(group => {
                    // 添加到过滤器
                    const filterOption = document.createElement('option');
                    filterOption.value = group.id;
                    filterOption.textContent = group.name;
                    groupFilter.appendChild(filterOption);
                    
                    // 添加到任务表单
                    const formOption = document.createElement('option');
                    formOption.value = group.id;
                    formOption.textContent = group.name;
                    taskGroup.appendChild(formOption);
                });
            })
            .catch(error => console.error('获取群组失败:', error));
    }
    
    // 加载用户选项
    function loadUsers() {
        fetch('/api/users/profiles/')
            .then(response => response.json())
            .then(data => {
                const assignUser = document.getElementById('assignUser');
                
                data.results.forEach(user => {
                    const option = document.createElement('option');
                    option.value = user.id;
                    option.textContent = user.username;
                    assignUser.appendChild(option);
                });
            })
            .catch(error => console.error('获取用户失败:', error));
    }
    
    // 加载代理选项
    function loadAgents() {
        fetch('/api/agents/agents/')
            .then(response => response.json())
            .then(data => {
                const assignAgent = document.getElementById('assignAgent');
                
                data.results.forEach(agent => {
                    const option = document.createElement('option');
                    option.value = agent.id;
                    option.textContent = agent.name;
                    assignAgent.appendChild(option);
                });
            })
            .catch(error => console.error('获取代理失败:', error));
    }
    
    // 加载父任务选项
    function loadParentTasks() {
        fetch(`${API_BASE_URL}/tasks/?is_parent=true`)
            .then(response => response.json())
            .then(data => {
                const taskParent = document.getElementById('taskParent');
                
                data.results.forEach(task => {
                    const option = document.createElement('option');
                    option.value = task.id;
                    option.textContent = task.title;
                    taskParent.appendChild(option);
                });
            })
            .catch(error => console.error('获取父任务失败:', error));
    }
    
    // 打开任务分配模态框
    function openAssignModal(taskId = null) {
        const assignTaskId = document.getElementById('assignTaskId');
        
        if (taskId) {
            // 单个任务分配
            assignTaskId.value = taskId;
        } else {
            // 批量分配，使用第一个选中的任务ID
            assignTaskId.value = Array.from(selectedTasks)[0];
        }
        
        assignTaskModal.show();
    }
    
    // 分配任务
    function assignTask() {
        const formData = new FormData(assignTaskForm);
        const taskId = formData.get('task');
        const assignType = formData.get('assignType');
        
        // 准备数据
        const data = {
            task: taskId,
            is_primary: formData.get('is_primary') === 'on',
            role: formData.get('role'),
            notes: formData.get('notes')
        };
        
        // 根据分配类型设置分配对象
        if (assignType === 'user') {
            data.assigned_user = formData.get('assigned_user');
        } else {
            data.assigned_agent = formData.get('assigned_agent');
        }
        
        // 发送请求
        fetch(`${API_BASE_URL}/assign-task/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) throw new Error('分配失败');
            return response.json();
        })
        .then(data => {
            showToast('任务分配成功', 'success');
            assignTaskModal.hide();
            
            // 如果是批量分配，继续分配其他任务
            if (selectedTasks.size > 1) {
                const taskIds = Array.from(selectedTasks);
                const currentIndex = taskIds.indexOf(taskId);
                
                if (currentIndex < taskIds.length - 1) {
                    document.getElementById('assignTaskId').value = taskIds[currentIndex + 1];
                    assignTask();
                } else {
                    // 全部分配完成，刷新任务列表
                    loadTasks();
                }
            } else {
                // 单个任务分配，刷新任务列表
                loadTasks();
            }
        })
        .catch(error => {
            console.error('分配任务失败:', error);
            showToast('分配任务失败，请重试', 'danger');
        });
    }
    
    // 编辑任务
    function editTask(taskId) {
        resetTaskForm();
        document.getElementById('taskModalLabel').textContent = '编辑任务';
        
        // 获取任务详情
        fetch(`${API_BASE_URL}/tasks/${taskId}/`)
            .then(response => {
                if (!response.ok) throw new Error('获取任务详情失败');
                return response.json();
            })
            .then(task => {
                // 填充表单
                document.getElementById('taskId').value = task.id;
                document.getElementById('taskTitle').value = task.title;
                document.getElementById('taskDescription').value = task.description || '';
                document.getElementById('taskStatus').value = task.status;
                document.getElementById('taskPriority').value = task.priority;
                document.getElementById('taskType').value = task.task_type;
                
                if (task.due_date) {
                    // 将日期时间格式化为HTML datetime-local输入格式
                    const dueDate = new Date(task.due_date);
                    const year = dueDate.getFullYear();
                    const month = String(dueDate.getMonth() + 1).padStart(2, '0');
                    const day = String(dueDate.getDate()).padStart(2, '0');
                    const hours = String(dueDate.getHours()).padStart(2, '0');
                    const minutes = String(dueDate.getMinutes()).padStart(2, '0');
                    
                    document.getElementById('taskDueDate').value = `${year}-${month}-${day}T${hours}:${minutes}`;
                }
                
                document.getElementById('taskGroup').value = task.group || '';
                document.getElementById('taskParent').value = task.parent_task || '';
                document.getElementById('taskProgress').value = task.progress || 0;
                document.getElementById('progressValue').textContent = task.progress || 0;
                document.getElementById('taskEstimatedHours').value = task.estimated_hours || '';
                document.getElementById('taskActualHours').value = task.actual_hours || '';
                
                // 显示模态框
                taskModal.show();
            })
            .catch(error => {
                console.error('获取任务详情失败:', error);
                showToast('获取任务详情失败，请重试', 'danger');
            });
    }
    
    // 保存任务
    function saveTask() {
        const formData = new FormData(taskForm);
        const taskId = formData.get('id');
        const isNewTask = !taskId;
        
        // 验证表单
        if (!formData.get('title')) {
            showToast('请输入任务标题', 'warning');
            return;
        }
        
        // 准备数据
        const data = {
            title: formData.get('title'),
            description: formData.get('description'),
            status: formData.get('status'),
            priority: formData.get('priority'),
            task_type: formData.get('task_type'),
            due_date: formData.get('due_date') || null,
            group: formData.get('group') || null,
            parent_task: formData.get('parent_task') || null,
            progress: parseInt(formData.get('progress')),
            estimated_hours: formData.get('estimated_hours') || null,
            actual_hours: formData.get('actual_hours') || null
        };
        
        // 确定URL和方法
        const url = isNewTask ? `${API_BASE_URL}/tasks/` : `${API_BASE_URL}/tasks/${taskId}/`;
        const method = isNewTask ? 'POST' : 'PUT';
        
        // 发送请求
        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) throw new Error('保存失败');
            return response.json();
        })
        .then(data => {
            showToast(`任务${isNewTask ? '创建' : '更新'}成功`, 'success');
            taskModal.hide();
            loadTasks();
        })
        .catch(error => {
            console.error('保存任务失败:', error);
            showToast(`任务${isNewTask ? '创建' : '更新'}失败，请重试`, 'danger');
        });
    }
    
    // 确认删除任务
    function confirmDeleteTask(taskId) {
        if (confirm('确定要删除此任务吗？此操作不可撤销。')) {
            deleteTask(taskId);
        }
    }
    
    // 删除任务
    function deleteTask(taskId) {
        fetch(`${API_BASE_URL}/tasks/${taskId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => {
            if (!response.ok) throw new Error('删除失败');
            showToast('任务删除成功', 'success');
            loadTasks();
        })
        .catch(error => {
            console.error('删除任务失败:', error);
            showToast('删除任务失败，请重试', 'danger');
        });
    }
    
    // 执行批量操作
    function performBulkAction(action, value) {
        if (selectedTasks.size === 0) return;
        
        const taskIds = Array.from(selectedTasks);
        const data = {
            task_ids: taskIds,
            action: action,
            value: value
        };
        
        fetch(`${API_BASE_URL}/bulk-update/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) throw new Error('批量操作失败');
            return response.json();
        })
        .then(data => {
            showToast(`成功更新 ${data.updated_count} 个任务`, 'success');
            loadTasks();
        })
        .catch(error => {
            console.error('批量操作失败:', error);
            showToast('批量操作失败，请重试', 'danger');
        });
    }
    
    // 更新批量操作状态
    function updateBulkActionState() {
        const bulkActionButtons = document.querySelectorAll('.bulk-action, #assignSelectedBtn, #addTagBtn');
        
        bulkActionButtons.forEach(button => {
            button.classList.toggle('disabled', selectedTasks.size === 0);
        });
    }
    
    // 重置任务表单
    function resetTaskForm() {
        taskForm.reset();
        document.getElementById('taskId').value = '';
        document.getElementById('progressValue').textContent = '0';
    }
    
    // 显示提示消息
    function showToast(message, type = 'info') {
        // 检查是否已有toast容器
        let toastContainer = document.querySelector('.toast-container');
        
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        // 创建toast元素
        const toastEl = document.createElement('div');
        toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        
        toastEl.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        toastContainer.appendChild(toastEl);
        
        // 初始化并显示toast
        const toast = new bootstrap.Toast(toastEl, {
            autohide: true,
            delay: 3000
        });
        
        toast.show();
        
        // 设置自动移除
        toastEl.addEventListener('hidden.bs.toast', function() {
            toastEl.remove();
        });
    }
    
    // 获取CSRF令牌
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
    
    // 状态文本
    function getStatusText(status) {
        const statusMap = {
            'pending': '待处理',
            'in_progress': '进行中',
            'review': '审核中',
            'completed': '已完成',
            'blocked': '已阻塞',
            'canceled': '已取消'
        };
        
        return statusMap[status] || status;
    }
    
    // 优先级文本
    function getPriorityText(priority) {
        const priorityMap = {
            'low': '低',
            'medium': '中',
            'high': '高',
            'urgent': '紧急'
        };
        
        return priorityMap[priority] || priority;
    }
}); 