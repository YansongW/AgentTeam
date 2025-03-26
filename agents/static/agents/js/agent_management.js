// agents/static/agents/js/agent_management.js

// 全局变量
let currentAgentId = null;
let agents = [];
let skills = [];

// 文档加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化页面
    loadAgents();
    setupEventListeners();
    
    // 初始化范围滑块
    const temperatureSlider = document.getElementById('temperatureSlider');
    if (temperatureSlider) {
        temperatureSlider.addEventListener('input', function() {
            document.getElementById('temperatureValue').textContent = this.value;
        });
    }
});

// 设置事件监听器
function setupEventListeners() {
    // 创建代理按钮点击事件
    document.getElementById('createAgentBtn').addEventListener('click', function() {
        openAgentModal();
    });
    
    // 保存代理按钮点击事件
    document.getElementById('saveAgentBtn').addEventListener('click', function() {
        saveAgent();
    });
    
    // 确认删除按钮点击事件
    document.getElementById('confirmDeleteBtn').addEventListener('click', function() {
        deleteAgent();
    });
    
    // 编辑代理按钮点击事件
    document.getElementById('editAgentBtn').addEventListener('click', function() {
        editAgent(currentAgentId);
    });
    
    // 聊天按钮点击事件
    document.getElementById('chatWithAgentBtn').addEventListener('click', function() {
        chatWithAgent(currentAgentId);
    });
    
    // 过滤器变化事件
    document.getElementById('roleFilter').addEventListener('change', function() {
        filterAgents();
    });
    
    document.getElementById('statusFilter').addEventListener('change', function() {
        filterAgents();
    });
    
    document.getElementById('searchAgent').addEventListener('input', function() {
        filterAgents();
    });
}

// API请求函数
async function apiRequest(url, method = 'GET', data = null) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        
        if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `API请求失败: ${response.status}`);
        }
        
        if (response.status === 204) {
            return null; // No content
        }
        
        return await response.json();
    } catch (error) {
        console.error('API请求出错:', error);
        showToast('错误', error.message, 'danger');
        throw error;
    }
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

// 显示提示消息
function showToast(title, message, type = 'success') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(container);
    }
    
    const toastId = 'toast-' + Date.now();
    const toastHTML = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <div class="bg-${type} rounded me-2" style="width:20px; height:20px;"></div>
                <strong class="me-auto">${title}</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    document.getElementById('toastContainer').insertAdjacentHTML('beforeend', toastHTML);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    toastElement.addEventListener('hidden.bs.toast', function () {
        toastElement.remove();
    });
}

// 加载代理列表
async function loadAgents() {
    try {
        showLoadingIndicator('agentsTable');
        agents = await apiRequest('/api/agents/');
        renderAgentsList(agents);
    } catch (error) {
        console.error('加载代理列表失败:', error);
        document.getElementById('agentsTableBody').innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-danger">加载代理列表失败，请刷新页面重试</td>
            </tr>
        `;
    } finally {
        hideLoadingIndicator('agentsTable');
    }
}

// 显示加载指示器
function showLoadingIndicator(tableId) {
    const tableBody = document.getElementById(`${tableId}Body`);
    if (tableBody) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">加载中...</span>
                    </div>
                    <p class="mt-2 text-muted">正在加载数据...</p>
                </td>
            </tr>
        `;
    }
}

// 隐藏加载指示器
function hideLoadingIndicator(tableId) {
    // 会被renderAgentsList替换，所以不需要额外操作
}

// 渲染代理列表
function renderAgentsList(agents) {
    const tableBody = document.getElementById('agentsTableBody');
    const noAgentsAlert = document.getElementById('noAgentsAlert');
    
    if (agents.length === 0) {
        tableBody.innerHTML = '';
        noAgentsAlert.style.display = 'block';
        return;
    }
    
    noAgentsAlert.style.display = 'none';
    let html = '';
    
    agents.forEach(agent => {
        html += `
            <tr data-agent-id="${agent.id}">
                <td>
                    <div class="d-flex align-items-center">
                        <span class="agent-status ${agent.status}"></span>
                        <a href="javascript:void(0)" class="agent-name-link" data-agent-id="${agent.id}">${agent.name}</a>
                    </div>
                </td>
                <td>${agent.role_display || agent.role}</td>
                <td>${getStatusBadge(agent.status)}</td>
                <td>${formatDate(agent.created_at)}</td>
                <td>${agent.is_public ? '<span class="badge bg-success">公开</span>' : '<span class="badge bg-secondary">私有</span>'}</td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        <button type="button" class="btn btn-outline-primary view-agent" data-agent-id="${agent.id}">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button type="button" class="btn btn-outline-secondary edit-agent" data-agent-id="${agent.id}">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button type="button" class="btn btn-outline-danger delete-agent" data-agent-id="${agent.id}">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });
    
    tableBody.innerHTML = html;
    
    // 添加事件监听器
    document.querySelectorAll('.view-agent, .agent-name-link').forEach(button => {
        button.addEventListener('click', function() {
            const agentId = this.getAttribute('data-agent-id');
            viewAgentDetails(agentId);
        });
    });
    
    document.querySelectorAll('.edit-agent').forEach(button => {
        button.addEventListener('click', function() {
            const agentId = this.getAttribute('data-agent-id');
            editAgent(agentId);
        });
    });
    
    document.querySelectorAll('.delete-agent').forEach(button => {
        button.addEventListener('click', function() {
            const agentId = this.getAttribute('data-agent-id');
            confirmDeleteAgent(agentId);
        });
    });
}

// 格式化日期
function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// 获取状态徽章
function getStatusBadge(status) {
    const statusMap = {
        'online': '<span class="badge bg-success">在线</span>',
        'offline': '<span class="badge bg-secondary">离线</span>',
        'busy': '<span class="badge bg-warning text-dark">忙碌</span>',
        'disabled': '<span class="badge bg-danger">已禁用</span>'
    };
    
    return statusMap[status] || `<span class="badge bg-light text-dark">${status}</span>`;
}

// 筛选代理列表
function filterAgents() {
    const roleFilter = document.getElementById('roleFilter').value;
    const statusFilter = document.getElementById('statusFilter').value;
    const searchText = document.getElementById('searchAgent').value.toLowerCase();
    
    const filtered = agents.filter(agent => {
        const roleMatch = !roleFilter || agent.role === roleFilter;
        const statusMatch = !statusFilter || agent.status === statusFilter;
        const searchMatch = !searchText || 
            agent.name.toLowerCase().includes(searchText) || 
            (agent.description && agent.description.toLowerCase().includes(searchText));
        
        return roleMatch && statusMatch && searchMatch;
    });
    
    renderAgentsList(filtered);
}

// 查看代理详情
async function viewAgentDetails(agentId) {
    try {
        const agent = await apiRequest(`/api/agents/${agentId}/`);
        currentAgentId = agent.id;
        
        // 填充基本信息
        document.getElementById('detailAgentName').textContent = agent.name;
        document.getElementById('detailAgentRole').textContent = agent.role_display || agent.role;
        document.getElementById('detailAgentStatus').textContent = getStatusText(agent.status);
        document.getElementById('detailAgentDescription').textContent = agent.description || '没有描述';
        document.getElementById('detailCreatedAt').textContent = formatDate(agent.created_at);
        document.getElementById('detailUpdatedAt').textContent = formatDate(agent.updated_at);
        document.getElementById('detailIsPublic').textContent = agent.is_public ? '公开' : '私有';
        
        // 填充系统提示词
        document.getElementById('detailSystemPrompt').textContent = agent.system_prompt || '没有设置系统提示词';
        
        // 填充模型配置
        const modelConfigEl = document.getElementById('detailModelConfig');
        if (agent.model_config && Object.keys(agent.model_config).length > 0) {
            let modelConfigHtml = '';
            for (const [key, value] of Object.entries(agent.model_config)) {
                modelConfigHtml += `
                    <li class="list-group-item d-flex justify-content-between align-items-center">
                        <span>${formatConfigKey(key)}</span>
                        <span class="badge bg-primary rounded-pill">${value}</span>
                    </li>
                `;
            }
            modelConfigEl.innerHTML = modelConfigHtml;
        } else {
            modelConfigEl.innerHTML = '<li class="list-group-item">使用默认模型配置</li>';
        }
        
        // 填充技能信息
        const skillsEl = document.getElementById('detailSkills');
        if (agent.skills && Object.keys(agent.skills).length > 0) {
            let skillsHtml = '';
            for (const [key, value] of Object.entries(agent.skills)) {
                skillsHtml += `
                    <li class="list-group-item d-flex justify-content-between align-items-center">
                        <span>${key}</span>
                        <span class="badge bg-${value ? 'success' : 'secondary'} rounded-pill">${value ? '已启用' : '已禁用'}</span>
                    </li>
                `;
            }
            skillsEl.innerHTML = skillsHtml;
        } else {
            skillsEl.innerHTML = '<li class="list-group-item">没有配置技能</li>';
        }
        
        // 填充API访问权限
        const apiAccessEl = document.getElementById('detailApiAccess');
        if (agent.api_access && Object.keys(agent.api_access).length > 0) {
            let apiAccessHtml = '';
            for (const [key, value] of Object.entries(agent.api_access)) {
                apiAccessHtml += `
                    <li class="list-group-item d-flex justify-content-between align-items-center">
                        <span>${formatConfigKey(key)}</span>
                        <span class="badge bg-${value ? 'success' : 'secondary'} rounded-pill">${value ? '允许' : '禁止'}</span>
                    </li>
                `;
            }
            apiAccessEl.innerHTML = apiAccessHtml;
        } else {
            apiAccessEl.innerHTML = '<li class="list-group-item">没有配置API访问权限</li>';
        }
        
        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('agentDetailModal'));
        modal.show();
    } catch (error) {
        console.error('加载代理详情失败:', error);
        showToast('错误', '加载代理详情失败: ' + error.message, 'danger');
    }
}

// 获取状态文本
function getStatusText(status) {
    const statusMap = {
        'online': '在线',
        'offline': '离线',
        'busy': '忙碌',
        'disabled': '已禁用'
    };
    
    return statusMap[status] || status;
}

// 格式化配置键名
function formatConfigKey(key) {
    // 将snake_case转换为人类可读的格式
    return key.split('_').map(word => 
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
}

// 打开代理编辑模态框
function openAgentModal(agent = null) {
    // 重置表单
    document.getElementById('agentForm').reset();
    document.getElementById('agentId').value = '';
    
    // 重置技能选择
    loadSkills();
    
    // 设置模态框标题
    document.getElementById('agentModalLabel').textContent = agent ? '编辑代理' : '创建新代理';
    
    // 如果是编辑模式，填充表单
    if (agent) {
        document.getElementById('agentId').value = agent.id;
        document.getElementById('agentName').value = agent.name;
        document.getElementById('agentRole').value = agent.role;
        document.getElementById('agentDescription').value = agent.description || '';
        document.getElementById('systemPrompt').value = agent.system_prompt || '';
        document.getElementById('agentStatus').value = agent.status;
        document.getElementById('isPublic').checked = agent.is_public;
        
        // 填充模型配置
        if (agent.model_config) {
            if (agent.model_config.model) {
                document.getElementById('modelName').value = agent.model_config.model;
            }
            
            if (agent.model_config.temperature) {
                const tempSlider = document.getElementById('temperatureSlider');
                tempSlider.value = agent.model_config.temperature;
                document.getElementById('temperatureValue').textContent = agent.model_config.temperature;
            }
            
            if (agent.model_config.max_tokens) {
                document.getElementById('maxTokens').value = agent.model_config.max_tokens;
            }
            
            if (agent.model_config.top_p) {
                document.getElementById('topP').value = agent.model_config.top_p;
            }
        }
        
        // 填充API访问权限
        if (agent.api_access) {
            document.getElementById('allowWebSearch').checked = !!agent.api_access.web_search;
            document.getElementById('allowFileAccess').checked = !!agent.api_access.file_access;
            document.getElementById('allowApiCalls').checked = !!agent.api_access.api_calls;
        }
    }
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('agentModal'));
    modal.show();
}

// 加载技能列表
async function loadSkills() {
    try {
        const skillsContainer = document.getElementById('skillsContainer');
        skillsContainer.innerHTML = `
            <div class="col-12 text-center py-3 skills-loading">
                <div class="spinner-border spinner-border-sm text-primary" role="status">
                    <span class="visually-hidden">加载中...</span>
                </div>
                <span class="text-muted ms-2">加载技能列表...</span>
            </div>
        `;
        
        skills = await apiRequest('/api/agents/skills/');
        
        let html = '';
        if (skills.length === 0) {
            html = '<div class="col-12"><div class="alert alert-info">当前系统中没有可用的技能。</div></div>';
        } else {
            skills.forEach(skill => {
                html += `
                    <div class="col-md-6 col-xl-4">
                        <div class="skill-card" data-skill-id="${skill.id}">
                            <div class="card-header">
                                <h5 class="skill-name">${skill.name}</h5>
                                <div class="form-check form-switch">
                                    <input class="form-check-input skill-toggle" type="checkbox" id="skill${skill.id}" data-skill-id="${skill.id}">
                                </div>
                            </div>
                            <div class="card-body">
                                <p class="skill-description">${skill.description || '没有描述'}</p>
                                <div class="custom-config-toggle">
                                    <input class="form-check-input me-2 config-toggle" type="checkbox" id="customConfig${skill.id}" data-skill-id="${skill.id}">
                                    <label class="form-check-label" for="customConfig${skill.id}">
                                        自定义配置
                                    </label>
                                </div>
                                <div class="custom-config-panel" id="configPanel${skill.id}">
                                    <textarea class="form-control" id="configText${skill.id}" rows="3" placeholder="输入JSON格式的配置"></textarea>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });
        }
        
        skillsContainer.innerHTML = html;
        
        // 添加事件监听器
        document.querySelectorAll('.config-toggle').forEach(toggle => {
            toggle.addEventListener('change', function() {
                const skillId = this.getAttribute('data-skill-id');
                const configPanel = document.getElementById(`configPanel${skillId}`);
                if (this.checked) {
                    configPanel.classList.add('show');
                } else {
                    configPanel.classList.remove('show');
                }
            });
        });
    } catch (error) {
        console.error('加载技能列表失败:', error);
        document.getElementById('skillsContainer').innerHTML = `
            <div class="col-12">
                <div class="alert alert-danger">加载技能列表失败，请刷新页面重试</div>
            </div>
        `;
    }
}

// 编辑代理
async function editAgent(agentId) {
    try {
        const agent = await apiRequest(`/api/agents/${agentId}/`);
        openAgentModal(agent);
    } catch (error) {
        console.error('加载代理详情失败:', error);
        showToast('错误', '加载代理详情失败: ' + error.message, 'danger');
    }
}

// 保存代理
async function saveAgent() {
    try {
        // 获取表单数据
        const agentId = document.getElementById('agentId').value;
        const name = document.getElementById('agentName').value;
        const role = document.getElementById('agentRole').value;
        const description = document.getElementById('agentDescription').value;
        const systemPrompt = document.getElementById('systemPrompt').value;
        const status = document.getElementById('agentStatus').value;
        const isPublic = document.getElementById('isPublic').checked;
        
        // 构建模型配置
        const modelConfig = {
            model: document.getElementById('modelName').value,
            temperature: parseFloat(document.getElementById('temperatureSlider').value),
            max_tokens: parseInt(document.getElementById('maxTokens').value),
            top_p: parseFloat(document.getElementById('topP').value)
        };
        
        // 构建API访问权限
        const apiAccess = {
            web_search: document.getElementById('allowWebSearch').checked,
            file_access: document.getElementById('allowFileAccess').checked,
            api_calls: document.getElementById('allowApiCalls').checked
        };
        
        // 构建技能配置
        const skillsConfig = {};
        document.querySelectorAll('.skill-toggle').forEach(toggle => {
            const skillId = toggle.getAttribute('data-skill-id');
            const isEnabled = toggle.checked;
            const customConfigToggle = document.getElementById(`customConfig${skillId}`);
            const hasCustomConfig = customConfigToggle && customConfigToggle.checked;
            
            if (isEnabled) {
                let config = true;
                if (hasCustomConfig) {
                    const configText = document.getElementById(`configText${skillId}`).value;
                    try {
                        config = configText ? JSON.parse(configText) : true;
                    } catch (e) {
                        throw new Error(`技能 ${skills.find(s => s.id == skillId).name} 的自定义配置不是有效的JSON格式`);
                    }
                }
                skillsConfig[skillId] = config;
            }
        });
        
        // 构建请求数据
        const data = {
            name,
            role,
            description,
            system_prompt: systemPrompt,
            status,
            is_public: isPublic,
            model_config: modelConfig,
            api_access: apiAccess,
            skills: skillsConfig
        };
        
        // 发送请求
        let response;
        if (agentId) {
            // 更新现有代理
            response = await apiRequest(`/api/agents/${agentId}/`, 'PUT', data);
            showToast('成功', `代理 "${name}" 已更新`, 'success');
        } else {
            // 创建新代理
            response = await apiRequest('/api/agents/', 'POST', data);
            showToast('成功', `代理 "${name}" 已创建`, 'success');
        }
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('agentModal'));
        modal.hide();
        
        // 重新加载代理列表
        loadAgents();
    } catch (error) {
        console.error('保存代理失败:', error);
        showToast('错误', '保存代理失败: ' + error.message, 'danger');
    }
}

// 确认删除代理
function confirmDeleteAgent(agentId) {
    currentAgentId = agentId;
    const agent = agents.find(a => a.id == agentId);
    if (agent) {
        document.getElementById('deleteAgentName').textContent = agent.name;
        const modal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
        modal.show();
    }
}

// 删除代理
async function deleteAgent() {
    if (!currentAgentId) return;
    
    try {
        await apiRequest(`/api/agents/${currentAgentId}/`, 'DELETE');
        showToast('成功', '代理已删除', 'success');
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(document.getElementById('deleteConfirmModal'));
        modal.hide();
        
        // 重新加载代理列表
        loadAgents();
    } catch (error) {
        console.error('删除代理失败:', error);
        showToast('错误', '删除代理失败: ' + error.message, 'danger');
    }
}

// 与代理聊天
function chatWithAgent(agentId) {
    window.location.href = `/chat/agent/${agentId}/`;
} 