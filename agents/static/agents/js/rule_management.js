// 规则管理JS

// 获取CSRF Token
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// 通用API请求函数
async function apiRequest(url, method = 'GET', data = null) {
    const headers = {
        'X-CSRFToken': getCSRFToken(),
        'Content-Type': 'application/json'
    };
    
    const options = {
        method: method,
        headers: headers,
        credentials: 'same-origin'
    };
    
    if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || `请求失败: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('API请求错误:', error);
        showNotification(`请求错误: ${error.message}`, 'danger');
        throw error;
    }
}

// 显示通知消息
function showNotification(message, type = 'success') {
    // 可以根据项目的通知系统进行适配
    alert(`${type.toUpperCase()}: ${message}`);
}

// 加载代理列表
async function loadAgents() {
    try {
        const agents = await apiRequest('/api/agents/');
        const agentSelect = document.getElementById('agentSelect');
        
        // 清空现有选项
        agentSelect.innerHTML = '<option value="">-- 请选择代理 --</option>';
        
        // 添加代理选项
        agents.forEach(agent => {
            const option = document.createElement('option');
            option.value = agent.id;
            option.textContent = agent.name;
            agentSelect.appendChild(option);
        });
    } catch (error) {
        console.error('加载代理列表失败:', error);
    }
}

// 加载规则列表
async function loadRules() {
    try {
        const rules = await apiRequest('/api/agent-rules/');
        const rulesTableBody = document.getElementById('rulesTableBody');
        const noRulesAlert = document.getElementById('noRulesAlert');
        const ruleSelect = document.getElementById('ruleSelect');
        
        // 清空现有内容
        rulesTableBody.innerHTML = '';
        ruleSelect.innerHTML = '<option value="">-- 请选择规则 --</option>';
        
        // 显示或隐藏提示信息
        if (rules.length === 0) {
            noRulesAlert.style.display = 'block';
            document.getElementById('rulesTable').style.display = 'none';
        } else {
            noRulesAlert.style.display = 'none';
            document.getElementById('rulesTable').style.display = 'table';
            
            // 填充规则表格
            rules.forEach(rule => {
                const row = document.createElement('tr');
                
                // 计算优先级类别
                let priorityClass = 'priority-medium';
                if (rule.priority <= 5) {
                    priorityClass = 'priority-high';
                } else if (rule.priority > 20) {
                    priorityClass = 'priority-low';
                }
                
                // 构建监听范围文本
                let listenScope = [];
                if (rule.listen_in_groups) listenScope.push('群组');
                if (rule.listen_in_direct) listenScope.push('直接消息');
                const listenScopeText = listenScope.join(', ');
                
                // 设置行内容
                row.innerHTML = `
                    <td>${rule.name}</td>
                    <td>${getTriggerTypeText(rule.trigger_type)}</td>
                    <td><span class="priority-badge ${priorityClass}">${rule.priority}</span></td>
                    <td><span class="rule-status-${rule.is_active ? 'active' : 'inactive'}">
                        ${rule.is_active ? '激活' : '禁用'}</span>
                    </td>
                    <td>${listenScopeText}</td>
                    <td>
                        <div class="btn-group btn-group-sm" role="group">
                            <button type="button" class="btn btn-outline-primary edit-rule" data-id="${rule.id}">编辑</button>
                            <button type="button" class="btn btn-outline-${rule.is_active ? 'warning' : 'success'} toggle-rule" data-id="${rule.id}">
                                ${rule.is_active ? '禁用' : '激活'}
                            </button>
                            <button type="button" class="btn btn-outline-danger delete-rule" data-id="${rule.id}">删除</button>
                        </div>
                    </td>
                `;
                
                rulesTableBody.appendChild(row);
                
                // 添加到测试选择框
                const option = document.createElement('option');
                option.value = rule.id;
                option.textContent = rule.name;
                ruleSelect.appendChild(option);
            });
            
            // 添加事件监听器
            addRuleTableEventListeners();
        }
    } catch (error) {
        console.error('加载规则列表失败:', error);
    }
}

// 获取触发类型的显示文本
function getTriggerTypeText(triggerType) {
    const typeMap = {
        'keyword': '关键词匹配',
        'regex': '正则表达式',
        'mention': '提及代理',
        'all_messages': '所有消息',
        'custom': '自定义条件'
    };
    return typeMap[triggerType] || triggerType;
}

// 获取响应类型的显示文本
function getResponseTypeText(responseType) {
    const typeMap = {
        'auto_reply': '自动回复',
        'notification': '通知',
        'task': '创建任务',
        'action': '执行动作',
        'custom': '自定义响应'
    };
    return typeMap[responseType] || responseType;
}

// 为规则表格中的按钮添加事件监听器
function addRuleTableEventListeners() {
    // 编辑按钮
    document.querySelectorAll('.edit-rule').forEach(button => {
        button.addEventListener('click', function() {
            const ruleId = this.getAttribute('data-id');
            editRule(ruleId);
        });
    });
    
    // 激活/禁用按钮
    document.querySelectorAll('.toggle-rule').forEach(button => {
        button.addEventListener('click', function() {
            const ruleId = this.getAttribute('data-id');
            toggleRuleActive(ruleId);
        });
    });
    
    // 删除按钮
    document.querySelectorAll('.delete-rule').forEach(button => {
        button.addEventListener('click', function() {
            const ruleId = this.getAttribute('data-id');
            deleteRule(ruleId);
        });
    });
}

// 编辑规则
async function editRule(ruleId) {
    try {
        const rule = await apiRequest(`/api/agent-rules/${ruleId}/`);
        
        // 设置模态框标题
        document.getElementById('ruleModalLabel').textContent = '编辑规则';
        
        // 填充表单
        document.getElementById('ruleId').value = rule.id;
        document.getElementById('agentSelect').value = rule.agent;
        document.getElementById('ruleName').value = rule.name;
        document.getElementById('ruleDescription').value = rule.description || '';
        document.getElementById('triggerType').value = rule.trigger_type;
        document.getElementById('responseType').value = rule.response_type;
        document.getElementById('rulePriority').value = rule.priority;
        document.getElementById('listenInGroups').checked = rule.listen_in_groups;
        document.getElementById('listenInDirect').checked = rule.listen_in_direct;
        document.getElementById('cooldownPeriod').value = rule.cooldown_period;
        
        // 根据触发类型显示相应的配置区域
        updateConditionConfig(rule.trigger_type, rule.trigger_condition);
        
        // 根据响应类型显示相应的配置区域
        updateResponseConfig(rule.response_type, rule.response_content);
        
        // 显示模态框
        const ruleModal = new bootstrap.Modal(document.getElementById('ruleModal'));
        ruleModal.show();
    } catch (error) {
        console.error('加载规则详情失败:', error);
    }
}

// 切换规则激活状态
async function toggleRuleActive(ruleId) {
    try {
        const result = await apiRequest(`/api/agent-rules/${ruleId}/toggle_active/`, 'POST');
        showNotification(`规则"${result.name}"已${result.is_active ? '激活' : '禁用'}`);
        loadRules(); // 重新加载规则列表
    } catch (error) {
        console.error('切换规则状态失败:', error);
    }
}

// 删除规则
async function deleteRule(ruleId) {
    if (!confirm('确定要删除这条规则吗？此操作不可撤销。')) {
        return;
    }
    
    try {
        await apiRequest(`/api/agent-rules/${ruleId}/`, 'DELETE');
        showNotification('规则已成功删除');
        loadRules(); // 重新加载规则列表
    } catch (error) {
        console.error('删除规则失败:', error);
    }
}

// 更新条件配置区域显示
function updateConditionConfig(triggerType, conditionData = {}) {
    // 先隐藏所有条件配置区域
    document.querySelectorAll('.condition-section').forEach(section => {
        section.style.display = 'none';
    });
    
    // 根据触发类型显示对应的条件配置
    switch (triggerType) {
        case 'keyword':
            document.getElementById('keywordCondition').style.display = 'block';
            // 加载已有关键词
            if (conditionData.keywords && Array.isArray(conditionData.keywords)) {
                const keywordsContainer = document.querySelector('.keywords-container');
                keywordsContainer.innerHTML = '';
                conditionData.keywords.forEach(keyword => {
                    addKeywordBadge(keywordsContainer, keyword);
                });
            }
            break;
            
        case 'regex':
            document.getElementById('regexCondition').style.display = 'block';
            if (conditionData.pattern) {
                document.getElementById('regexPattern').value = conditionData.pattern;
            }
            break;
            
        case 'sentiment':
            document.getElementById('sentimentCondition').style.display = 'block';
            if (conditionData.target_sentiment) {
                document.getElementById('sentimentType').value = conditionData.target_sentiment;
            }
            if (conditionData.threshold) {
                document.getElementById('sentimentThreshold').value = conditionData.threshold;
            }
            break;
            
        case 'context_aware':
            document.getElementById('contextAwareCondition').style.display = 'block';
            // 加载上下文关键词
            if (conditionData.context_keywords && Array.isArray(conditionData.context_keywords)) {
                const contextKeywordsContainer = document.querySelector('.context-keywords-container');
                contextKeywordsContainer.innerHTML = '';
                conditionData.context_keywords.forEach(keyword => {
                    addKeywordBadge(contextKeywordsContainer, keyword);
                });
            }
            if (conditionData.context_size) {
                document.getElementById('contextSize').value = conditionData.context_size;
            }
            if (conditionData.match_threshold) {
                document.getElementById('matchThreshold').value = conditionData.match_threshold;
            }
            break;
            
        // 其他触发类型的配置...
    }
}

// 根据响应类型更新响应配置区域
function updateResponseConfig(responseType, responseData = {}) {
    // 隐藏所有响应配置区域
    document.querySelectorAll('.response-section').forEach(section => {
        section.style.display = 'none';
    });
    
    // 显示对应的响应配置区域
    if (responseType === 'auto_reply') {
        const replySection = document.getElementById('autoReplyResponse');
        replySection.style.display = 'block';
        
        // 设置回复模板
        document.getElementById('replyTemplate').value = responseData.reply_template || '';
    }
    // 其他响应类型的处理...
}

// 添加关键词标签
function addKeywordBadge(container, keyword) {
    const badge = document.createElement('div');
    badge.className = 'keyword-badge';
    badge.innerHTML = `
        ${keyword}
        <button type="button" class="remove-keyword">&times;</button>
    `;
    
    // 添加删除按钮事件
    badge.querySelector('.remove-keyword').addEventListener('click', function() {
        badge.remove();
    });
    
    container.appendChild(badge);
}

// 收集表单数据
function collectFormData() {
    const ruleId = document.getElementById('ruleId').value;
    const agent = document.getElementById('agentSelect').value;
    const name = document.getElementById('ruleName').value;
    const description = document.getElementById('ruleDescription').value;
    const triggerType = document.getElementById('triggerType').value;
    const responseType = document.getElementById('responseType').value;
    const priority = document.getElementById('rulePriority').value;
    const listenInGroups = document.getElementById('listenInGroups').checked;
    const listenInDirect = document.getElementById('listenInDirect').checked;
    const cooldownPeriod = document.getElementById('cooldownPeriod').value;
    
    // 收集触发条件数据
    let triggerCondition = {};
    
    switch (triggerType) {
        case 'keyword':
            // 收集关键词
            const keywordBadges = document.querySelectorAll('.keywords-container .badge');
            triggerCondition.keywords = Array.from(keywordBadges).map(badge => badge.dataset.keyword);
            break;
            
        case 'regex':
            // 收集正则表达式
            triggerCondition.pattern = document.getElementById('regexPattern').value;
            break;
            
        case 'sentiment':
            // 收集情绪分析配置
            triggerCondition.target_sentiment = document.getElementById('sentimentType').value;
            triggerCondition.threshold = parseFloat(document.getElementById('sentimentThreshold').value);
            break;
            
        case 'context_aware':
            // 收集上下文感知配置
            const contextKeywordBadges = document.querySelectorAll('.context-keywords-container .badge');
            triggerCondition.context_keywords = Array.from(contextKeywordBadges).map(badge => badge.dataset.keyword);
            triggerCondition.context_size = parseInt(document.getElementById('contextSize').value);
            triggerCondition.match_threshold = parseFloat(document.getElementById('matchThreshold').value);
            break;
            
        // 其他触发类型数据收集...
    }
    
    // 收集响应数据
    let responseContent = {};
    
    switch (responseType) {
        case 'auto_reply':
            responseContent.reply_template = document.getElementById('replyTemplate').value;
            break;
            
        // 其他响应类型数据收集...
    }
    
    // 构建规则数据对象
    const ruleData = {
        name,
        description,
        agent,
        is_active: true,
        priority: parseInt(priority),
        trigger_type: triggerType,
        trigger_condition: triggerCondition,
        response_type: responseType,
        response_content: responseContent,
        listen_in_groups: listenInGroups,
        listen_in_direct: listenInDirect,
        cooldown_period: parseInt(cooldownPeriod)
    };
    
    if (ruleId) {
        ruleData.id = ruleId;
    }
    
    return ruleData;
}

// 测试规则
async function testRule(ruleId, messageData) {
    try {
        const result = await apiRequest(`/api/agent-rules/${ruleId}/test_rule/`, 'POST', {
            message: messageData,
            apply_transformation: document.getElementById('applyTransformation').checked
        });
        
        // 显示测试结果
        const resultContainer = document.getElementById('testResultContainer');
        const resultContent = document.getElementById('testResultContent');
        
        resultContainer.style.display = 'block';
        resultContent.textContent = JSON.stringify(result, null, 2);
        
        // 根据匹配结果添加样式
        resultContainer.className = result.matches ? 'alert alert-success' : 'alert alert-warning';
    } catch (error) {
        console.error('测试规则失败:', error);
    }
}

// 保存规则
async function saveRule() {
    try {
        const formData = collectFormData();
        const isNew = !formData.id;
        
        let url = '/api/agent-rules/';
        let method = 'POST';
        
        if (!isNew) {
            url = `/api/agent-rules/${formData.id}/`;
            method = 'PUT';
            delete formData.id; // 删除ID字段，避免API错误
        }
        
        const result = await apiRequest(url, method, formData);
        
        // 关闭模态框
        const ruleModal = bootstrap.Modal.getInstance(document.getElementById('ruleModal'));
        ruleModal.hide();
        
        // 显示成功消息
        showNotification(`规则"${result.name}"已${isNew ? '创建' : '更新'}`);
        
        // 重新加载规则列表
        loadRules();
    } catch (error) {
        console.error('保存规则失败:', error);
    }
}

// 打开规则创建/编辑模态框
function openRuleModal(ruleId = null) {
    // 重置表单
    document.getElementById('ruleForm').reset();
    document.getElementById('ruleId').value = '';
    
    // 设置标题
    if (ruleId) {
        document.getElementById('ruleModalLabel').textContent = '编辑规则';
    } else {
        document.getElementById('ruleModalLabel').textContent = '创建规则';
    }
    
    // 显示默认的配置区域
    updateConditionConfig('keyword');
    updateResponseConfig('auto_reply');
    
    // 显示模态框
    const ruleModal = new bootstrap.Modal(document.getElementById('ruleModal'));
    ruleModal.show();
    
    // 如果是编辑模式，加载规则数据
    if (ruleId) {
        loadRuleForEdit(ruleId);
    }
}

// 文档加载完成后的处理
document.addEventListener('DOMContentLoaded', function() {
    // 加载代理和规则列表
    loadAgents();
    loadRules();
    
    // 添加事件监听器
    document.getElementById('createRuleBtn').addEventListener('click', function() {
        openRuleModal();
    });
    
    document.getElementById('saveRuleBtn').addEventListener('click', saveRule);
    
    // 添加关键词按钮事件
    document.querySelector('.add-keyword-btn').addEventListener('click', function() {
        const input = document.querySelector('.keyword-input');
        const keyword = input.value.trim();
        
        if (keyword) {
            const container = document.querySelector('.keywords-container');
            addKeywordBadge(container, keyword);
            input.value = '';
        }
    });
    
    // 添加上下文关键词按钮事件
    document.querySelector('.add-context-keyword-btn').addEventListener('click', function() {
        const input = document.querySelector('.context-keyword-input');
        const keyword = input.value.trim();
        
        if (keyword) {
            const container = document.querySelector('.context-keywords-container');
            addKeywordBadge(container, keyword);
            input.value = '';
        }
    });
    
    // 情绪阈值滑块事件
    document.getElementById('sentimentThreshold').addEventListener('input', function() {
        document.getElementById('sentimentThresholdValue').textContent = this.value;
    });
    
    // 匹配阈值滑块事件
    document.getElementById('matchThreshold').addEventListener('input', function() {
        document.getElementById('matchThresholdValue').textContent = this.value;
    });
    
    // 触发类型变更事件
    document.getElementById('triggerType').addEventListener('change', function() {
        updateConditionConfig(this.value);
    });
    
    // 响应类型变更事件
    document.getElementById('responseType').addEventListener('change', function() {
        updateResponseConfig(this.value);
    });
    
    // 测试规则表单提交事件
    document.getElementById('ruleTestForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const ruleId = document.getElementById('ruleSelect').value;
        const messageContent = document.getElementById('messageContent').value;
        const messageType = document.getElementById('messageType').value;
        const applyTransformation = document.getElementById('applyTransformation').checked;
        
        if (!ruleId || !messageContent) {
            showNotification('请选择规则并输入测试消息', 'warning');
            return;
        }
        
        // 创建测试消息数据
        const messageData = {
            content: messageContent,
            type: messageType,
            apply_transformation: applyTransformation
        };
        
        testRule(ruleId, messageData);
    });
    
    // 初始化规则表格事件监听
    addRuleTableEventListeners();
}); 