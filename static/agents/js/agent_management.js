/**
 * Agent管理页面JavaScript
 */

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 页面DOM元素
    const agentList = document.getElementById('agentList');
    const noAgentsAlert = document.getElementById('noAgentsAlert');
    const searchAgent = document.getElementById('searchAgent');
    const roleFilter = document.getElementById('roleFilter');
    const statusFilter = document.getElementById('statusFilter');
    const resetFiltersBtn = document.getElementById('resetFilters');
    const createAgentBtn = document.getElementById('createAgentBtn');
    const agentModal = document.getElementById('agentModal');
    const agentModalLabel = document.getElementById('agentModalLabel');
    const agentForm = document.getElementById('agentForm');
    const saveAgentBtn = document.getElementById('saveAgentBtn');
    const deleteAgentModal = document.getElementById('deleteAgentModal');
    const confirmDeleteAgent = document.getElementById('confirmDeleteAgent');
    const toastContainer = document.getElementById('toastContainer');
    
    // 温度滑块值显示
    const temperatureSlider = document.getElementById('temperatureSlider');
    const temperatureValue = document.getElementById('temperatureValue');
    if (temperatureSlider && temperatureValue) {
        temperatureSlider.addEventListener('input', function() {
            temperatureValue.textContent = this.value;
        });
    }
    
    // 知识库开关控制
    const enableKnowledgeBase = document.getElementById('enableKnowledgeBase');
    const knowledgeBaseSettings = document.getElementById('knowledgeBaseSettings');
    if (enableKnowledgeBase && knowledgeBaseSettings) {
        enableKnowledgeBase.addEventListener('change', function() {
            knowledgeBaseSettings.style.display = this.checked ? 'block' : 'none';
        });
    }

    // 模态框实例
    const agentModalInstance = new bootstrap.Modal(agentModal);
    const deleteModalInstance = new bootstrap.Modal(deleteAgentModal);
    
    // 加载代理列表
    function loadAgents() {
        fetch('/api/agents/')
            .then(response => response.json())
            .then(data => {
                if (data.length === 0) {
                    noAgentsAlert.style.display = 'block';
                    agentList.innerHTML = '';
                } else {
                    noAgentsAlert.style.display = 'none';
                    renderAgentCards(data);
                }
            })
            .catch(error => {
                console.error('加载代理出错:', error);
                showToast('加载代理失败，请刷新页面重试', 'danger');
            });
    }
    
    // 渲染代理卡片
    function renderAgentCards(agents) {
        const searchTerm = searchAgent.value.toLowerCase();
        const roleValue = roleFilter.value;
        const statusValue = statusFilter.value;
        
        // 过滤代理
        const filteredAgents = agents.filter(agent => {
            const nameMatch = agent.name.toLowerCase().includes(searchTerm) || 
                            (agent.description && agent.description.toLowerCase().includes(searchTerm));
            const roleMatch = !roleValue || agent.role === roleValue;
            const statusMatch = !statusValue || agent.status === statusValue;
            return nameMatch && roleMatch && statusMatch;
        });
        
        // 清空当前列表
        agentList.innerHTML = '';
        
        if (filteredAgents.length === 0) {
            agentList.innerHTML = `
                <div class="col-12">
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i> 未找到匹配的代理
                    </div>
                </div>
            `;
            return;
        }
        
        // 创建代理卡片
        filteredAgents.forEach(agent => {
            const card = document.createElement('div');
            card.className = 'col-lg-4 col-md-6 mb-4';
            card.innerHTML = `
                <div class="agent-card">
                    <div class="agent-header d-flex justify-content-between align-items-start">
                        <div>
                            <h5 class="mb-1">${agent.name}</h5>
                            <div class="text-muted small">${getRoleName(agent.role)}</div>
                        </div>
                        <div class="agent-status agent-status-${agent.status}">
                            ${getStatusName(agent.status)}
                        </div>
                    </div>
                    <div class="p-3">
                        <p class="mb-3 agent-description">${agent.description || '无描述'}</p>
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <div class="text-muted small">创建于 ${formatDate(agent.created_at)}</div>
                            <div>${agent.is_public ? '<span class="badge bg-primary">公开</span>' : '<span class="badge bg-secondary">私有</span>'}</div>
                        </div>
                        <div class="agent-skills mb-3">
                            ${agent.skills && agent.skills.length > 0 ? 
                                agent.skills.slice(0, 3).map(skill => `
                                    <span class="skill-item">${skill.name}</span>
                                `).join('') + 
                                (agent.skills.length > 3 ? `<span class="skill-item">+${agent.skills.length - 3}</span>` : '')
                                : '<span class="text-muted small">无技能</span>'
                            }
                        </div>
                        <div class="d-flex">
                            <button class="btn btn-sm btn-outline-primary me-2 btn-action chat-btn" data-agent-id="${agent.id}">
                                <i class="fas fa-comment me-1"></i> 聊天
                            </button>
                            <button class="btn btn-sm btn-outline-secondary me-2 btn-action edit-btn" data-agent-id="${agent.id}">
                                <i class="fas fa-edit me-1"></i> 编辑
                            </button>
                            <button class="btn btn-sm btn-outline-danger btn-action delete-btn" data-agent-id="${agent.id}" data-agent-name="${agent.name}">
                                <i class="fas fa-trash-alt me-1"></i> 删除
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            // 添加事件监听器
            agentList.appendChild(card);
            
            // 聊天按钮
            const chatBtn = card.querySelector('.chat-btn');
            chatBtn.addEventListener('click', () => {
                window.location.href = `/chat/?agent_id=${agent.id}`;
            });
            
            // 编辑按钮
            const editBtn = card.querySelector('.edit-btn');
            editBtn.addEventListener('click', () => {
                openEditAgentModal(agent.id);
            });
            
            // 删除按钮
            const deleteBtn = card.querySelector('.delete-btn');
            deleteBtn.addEventListener('click', () => {
                openDeleteAgentModal(agent.id, agent.name);
            });
        });
    }
    
    // 获取角色名称
    function getRoleName(role) {
        const roleMap = {
            'product_manager': '产品经理',
            'frontend_dev': '前端开发',
            'backend_dev': '后端开发',
            'ux_designer': '用户体验设计师',
            'qa_tester': '测试工程师',
            'data_analyst': '数据分析师',
            'virtual_friend': '虚拟朋友',
            'assistant': '助手',
            'custom': '自定义'
        };
        return roleMap[role] || role;
    }
    
    // 获取状态名称
    function getStatusName(status) {
        const statusMap = {
            'online': '在线',
            'offline': '离线',
            'busy': '忙碌',
            'disabled': '已禁用'
        };
        return statusMap[status] || status;
    }
    
    // 格式化日期
    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('zh-CN');
    }
    
    // 加载技能列表
    function loadSkills() {
        const skillsContainer = document.getElementById('skillsContainer');
        if (!skillsContainer) return;
        
        fetch('/api/skills/')
            .then(response => response.json())
            .then(data => {
                skillsContainer.innerHTML = '';
                data.forEach(skill => {
                    const skillCol = document.createElement('div');
                    skillCol.className = 'col-md-4 mb-2';
                    skillCol.innerHTML = `
                        <div class="form-check">
                            <input class="form-check-input skill-checkbox" type="checkbox" value="${skill.id}" id="skill-${skill.id}">
                            <label class="form-check-label" for="skill-${skill.id}">
                                ${skill.name}
                            </label>
                            <small class="d-block text-muted">${skill.description}</small>
                        </div>
                    `;
                    skillsContainer.appendChild(skillCol);
                });
            })
            .catch(error => {
                console.error('加载技能出错:', error);
                skillsContainer.innerHTML = '<div class="col-12"><div class="alert alert-danger">加载技能失败</div></div>';
            });
    }
    
    // 加载知识库列表
    function loadKnowledgeBases() {
        const select = document.getElementById('knowledgeBaseSelect');
        if (!select) return;
        
        fetch('/api/knowledge_bases/')
            .then(response => response.json())
            .then(data => {
                // 保留第一个选项
                const firstOption = select.options[0];
                select.innerHTML = '';
                select.appendChild(firstOption);
                
                data.forEach(kb => {
                    const option = document.createElement('option');
                    option.value = kb.id;
                    option.textContent = kb.name;
                    select.appendChild(option);
                });
            })
            .catch(error => {
                console.error('加载知识库出错:', error);
            });
    }
    
    // 打开编辑代理模态框
    function openEditAgentModal(agentId = null) {
        // 重置表单
        agentForm.reset();
        document.getElementById('agentId').value = '';
        
        if (agentId) {
            // 编辑现有代理
            agentModalLabel.textContent = '编辑代理';
            
            // 加载代理数据
            fetch(`/api/agents/${agentId}/`)
                .then(response => response.json())
                .then(agent => {
                    document.getElementById('agentId').value = agent.id;
                    document.getElementById('agentName').value = agent.name;
                    document.getElementById('agentRole').value = agent.role;
                    document.getElementById('agentDescription').value = agent.description || '';
                    document.getElementById('systemPrompt').value = agent.system_prompt || '';
                    document.getElementById('agentStatus').value = agent.status;
                    document.getElementById('isPublic').checked = agent.is_public;
                    
                    // 设置模型配置
                    if (agent.model_config) {
                        document.getElementById('modelName').value = agent.model_config.model_name || 'gpt-4';
                        document.getElementById('temperatureSlider').value = agent.model_config.temperature || 0.7;
                        temperatureValue.textContent = agent.model_config.temperature || 0.7;
                        document.getElementById('maxTokens').value = agent.model_config.max_tokens || 1000;
                        document.getElementById('topP').value = agent.model_config.top_p || 0.9;
                    }
                    
                    // 设置知识库配置
                    if (agent.knowledge_base) {
                        document.getElementById('enableKnowledgeBase').checked = true;
                        knowledgeBaseSettings.style.display = 'block';
                        document.getElementById('knowledgeBaseSelect').value = agent.knowledge_base.id;
                    } else {
                        document.getElementById('enableKnowledgeBase').checked = false;
                        knowledgeBaseSettings.style.display = 'none';
                    }
                    
                    // 设置技能
                    if (agent.skills && agent.skills.length > 0) {
                        agent.skills.forEach(skill => {
                            const checkbox = document.getElementById(`skill-${skill.id}`);
                            if (checkbox) checkbox.checked = true;
                        });
                    }
                })
                .catch(error => {
                    console.error('加载代理详情出错:', error);
                    showToast('加载代理详情失败', 'danger');
                });
        } else {
            // 创建新代理
            agentModalLabel.textContent = '创建新代理';
        }
        
        // 打开模态框
        agentModalInstance.show();
    }
    
    // 打开删除代理模态框
    function openDeleteAgentModal(agentId, agentName) {
        document.getElementById('deleteAgentMessage').textContent = `确定要删除代理 "${agentName}" 吗？此操作无法撤销。`;
        confirmDeleteAgent.dataset.agentId = agentId;
        deleteModalInstance.show();
    }
    
    // 保存代理
    function saveAgent() {
        // 获取表单数据
        const agentId = document.getElementById('agentId').value;
        const agentData = {
            name: document.getElementById('agentName').value,
            role: document.getElementById('agentRole').value,
            description: document.getElementById('agentDescription').value,
            system_prompt: document.getElementById('systemPrompt').value,
            status: document.getElementById('agentStatus').value,
            is_public: document.getElementById('isPublic').checked,
            model_config: {
                model_name: document.getElementById('modelName').value,
                temperature: parseFloat(document.getElementById('temperatureSlider').value),
                max_tokens: parseInt(document.getElementById('maxTokens').value),
                top_p: parseFloat(document.getElementById('topP').value)
            }
        };
        
        // 获取选中的技能
        const selectedSkills = [];
        document.querySelectorAll('.skill-checkbox:checked').forEach(checkbox => {
            selectedSkills.push(parseInt(checkbox.value));
        });
        agentData.skills = selectedSkills;
        
        // 知识库配置
        if (document.getElementById('enableKnowledgeBase').checked) {
            const knowledgeBaseId = document.getElementById('knowledgeBaseSelect').value;
            if (knowledgeBaseId) {
                agentData.knowledge_base_id = knowledgeBaseId;
            }
        }
        
        // 发送请求
        const url = agentId ? `/api/agents/${agentId}/` : '/api/agents/';
        const method = agentId ? 'PUT' : 'POST';
        
        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(agentData)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(JSON.stringify(err));
                });
            }
            return response.json();
        })
        .then(data => {
            agentModalInstance.hide();
            showToast(`代理${agentId ? '更新' : '创建'}成功`, 'success');
            loadAgents();
        })
        .catch(error => {
            console.error('保存代理出错:', error);
            let errorMessage = '保存失败';
            try {
                const errorObj = JSON.parse(error.message);
                errorMessage = Object.values(errorObj).flat().join(', ');
            } catch (e) {
                errorMessage = error.message;
            }
            showToast(errorMessage, 'danger');
        });
    }
    
    // 删除代理
    function deleteAgent(agentId) {
        fetch(`/api/agents/${agentId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('删除失败');
            }
            deleteModalInstance.hide();
            showToast('代理删除成功', 'success');
            loadAgents();
        })
        .catch(error => {
            console.error('删除代理出错:', error);
            showToast('删除代理失败', 'danger');
        });
    }
    
    // 获取CSRF Token
    function getCsrfToken() {
        return document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '';
    }
    
    // 显示提示消息
    function showToast(message, type = 'info') {
        const toastId = 'toast-' + Date.now();
        const toastHtml = `
            <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true" data-bs-autohide="true" data-bs-delay="3000">
                <div class="toast-header bg-${type} text-white">
                    <strong class="me-auto">${type === 'danger' ? '错误' : '提示'}</strong>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="关闭"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;
        
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
        
        // 自动移除toast元素
        toastElement.addEventListener('hidden.bs.toast', function() {
            toastElement.remove();
        });
    }
    
    // 事件监听器
    if (searchAgent) {
        searchAgent.addEventListener('input', () => {
            loadAgents();
        });
    }
    
    if (roleFilter) {
        roleFilter.addEventListener('change', () => {
            loadAgents();
        });
    }
    
    if (statusFilter) {
        statusFilter.addEventListener('change', () => {
            loadAgents();
        });
    }
    
    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', () => {
            searchAgent.value = '';
            roleFilter.value = '';
            statusFilter.value = '';
            loadAgents();
        });
    }
    
    if (createAgentBtn) {
        createAgentBtn.addEventListener('click', () => {
            openEditAgentModal();
        });
    }
    
    if (saveAgentBtn) {
        saveAgentBtn.addEventListener('click', () => {
            saveAgent();
        });
    }
    
    if (confirmDeleteAgent) {
        confirmDeleteAgent.addEventListener('click', () => {
            const agentId = confirmDeleteAgent.dataset.agentId;
            if (agentId) {
                deleteAgent(agentId);
            }
        });
    }
    
    // 初始化
    loadAgents();
    loadSkills();
    loadKnowledgeBases();
}); 