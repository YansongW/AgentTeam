/**
 * 规则管理页面JavaScript
 */

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // DOM元素
    const ruleList = document.getElementById('ruleList');
    const createRuleForm = document.getElementById('createRuleForm');
    const editRuleForm = document.getElementById('editRuleForm');
    const deleteRuleModal = document.getElementById('deleteRuleModal');
    const testRuleForm = document.getElementById('testRuleForm');
    const testResultContent = document.getElementById('testResultContent');
    
    let keywordsInput = document.getElementById('keywords');
    let contextKeywordsInput = document.getElementById('contextKeywords');
    let keywordsContainer = document.querySelector('.keywords-container');
    let contextKeywordsContainer = document.querySelector('.context-keywords-container');
    
    let editKeywordsInput = document.getElementById('editKeywords');
    let editContextKeywordsInput = document.getElementById('editContextKeywords');
    let editKeywordsContainer = document.querySelector('.edit-keywords-container');
    let editContextKeywordsContainer = document.querySelector('.edit-context-keywords-container');
    
    // CSRF Token获取函数
    function getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }
    
    // 加载规则列表
    function loadRules() {
        fetch('/api/agent-rules/')
            .then(response => response.json())
            .then(data => {
                displayRules(data);
            })
            .catch(error => {
                console.error('获取规则列表失败:', error);
                showToast('error', '获取规则列表失败');
            });
    }
    
    // 显示规则列表
    function displayRules(rules) {
        if (!ruleList) return;
        
        ruleList.innerHTML = '';
        
        if (rules.length === 0) {
            ruleList.innerHTML = '<tr><td colspan="6" class="text-center">暂无规则数据</td></tr>';
            return;
        }
        
        rules.forEach(rule => {
            // 格式化关键词
            const keywords = formatKeywords(rule.keywords);
            const contextKeywords = formatKeywords(rule.context_keywords);
            
            // 优先级和状态样式
            const priorityClass = getPriorityClass(rule.priority);
            const statusClass = getStatusClass(rule.is_active);
            
            // 创建表格行
            const row = document.createElement('tr');
            row.className = 'fade-in';
            row.innerHTML = `
                <td>${rule.name}</td>
                <td>
                    ${keywords}
                    ${contextKeywords ? `<div class="mt-1"><small class="text-muted">上下文: ${contextKeywords}</small></div>` : ''}
                </td>
                <td>
                    <span class="${priorityClass}">${formatPriority(rule.priority)}</span>
                </td>
                <td>
                    <span class="${statusClass}">${rule.is_active ? '启用' : '禁用'}</span>
                </td>
                <td>
                    ${formatScope(rule.scope, rule.groups)}
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary test-rule" data-rule-id="${rule.id}">
                            <i class="fas fa-vial"></i>
                        </button>
                        <button class="btn btn-outline-secondary edit-rule" data-rule-id="${rule.id}">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-outline-danger delete-rule" data-rule-id="${rule.id}" data-rule-name="${rule.name}">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                </td>
            `;
            
            ruleList.appendChild(row);
        });
        
        // 添加事件监听器
        document.querySelectorAll('.edit-rule').forEach(btn => {
            btn.addEventListener('click', function() {
                const ruleId = this.getAttribute('data-rule-id');
                editRule(ruleId);
            });
        });
        
        document.querySelectorAll('.delete-rule').forEach(btn => {
            btn.addEventListener('click', function() {
                const ruleId = this.getAttribute('data-rule-id');
                const ruleName = this.getAttribute('data-rule-name');
                showDeleteModal(ruleId, ruleName);
            });
        });
        
        document.querySelectorAll('.test-rule').forEach(btn => {
            btn.addEventListener('click', function() {
                const ruleId = this.getAttribute('data-rule-id');
                showTestModal(ruleId);
            });
        });
    }
    
    // 格式化关键词显示
    function formatKeywords(keywords) {
        if (!keywords || keywords.length === 0) return '';
        
        return keywords.map(keyword => {
            return `<span class="keyword-badge">${keyword}</span>`;
        }).join(' ');
    }
    
    // 获取优先级样式
    function getPriorityClass(priority) {
        switch(priority) {
            case 'high': return 'rule-priority-high';
            case 'medium': return 'rule-priority-medium';
            case 'low': return 'rule-priority-low';
            default: return '';
        }
    }
    
    // 格式化优先级显示
    function formatPriority(priority) {
        switch(priority) {
            case 'high': return '高';
            case 'medium': return '中';
            case 'low': return '低';
            default: return priority;
        }
    }
    
    // 获取状态样式
    function getStatusClass(isActive) {
        return isActive ? 'rule-status-active' : 'rule-status-inactive';
    }
    
    // 格式化规则作用域
    function formatScope(scope, groups) {
        if (scope === 'global') {
            return '全局';
        } else if (scope === 'groups' && groups && groups.length > 0) {
            const groupText = groups.length > 2 ? 
                `${groups.length}个群组` : 
                groups.map(g => g.name).join(', ');
            
            return `<span class="rule-scope-groups">${groupText}</span>`;
        } else if (scope === 'direct') {
            return '<span class="rule-scope-direct">直接@</span>';
        }
        return scope;
    }
    
    // 关键词输入处理
    function setupKeywordInputs() {
        // 创建表单关键词
        if (keywordsInput && keywordsContainer) {
            keywordsInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    addKeyword(this.value, keywordsContainer, 'keyword');
                    this.value = '';
                }
            });
        }
        
        if (contextKeywordsInput && contextKeywordsContainer) {
            contextKeywordsInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    addKeyword(this.value, contextKeywordsContainer, 'context-keyword');
                    this.value = '';
                }
            });
        }
        
        // 编辑表单关键词
        if (editKeywordsInput && editKeywordsContainer) {
            editKeywordsInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    addKeyword(this.value, editKeywordsContainer, 'keyword');
                    this.value = '';
                }
            });
        }
        
        if (editContextKeywordsInput && editContextKeywordsContainer) {
            editContextKeywordsInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    addKeyword(this.value, editContextKeywordsContainer, 'context-keyword');
                    this.value = '';
                }
            });
        }
    }
    
    // 添加关键词
    function addKeyword(text, container, type) {
        if (!text.trim()) return;
        
        const keyword = document.createElement('span');
        keyword.className = 'keyword-badge';
        keyword.innerHTML = `
            ${text.trim()}
            <span class="remove-keyword" data-keyword="${text.trim()}" data-type="${type}">
                <i class="fas fa-times"></i>
            </span>
        `;
        
        container.appendChild(keyword);
        
        // 添加删除事件
        keyword.querySelector('.remove-keyword').addEventListener('click', function() {
            this.parentNode.remove();
        });
    }
    
    // 从容器获取关键词列表
    function getKeywordsFromContainer(container) {
        const keywords = [];
        container.querySelectorAll('.keyword-badge').forEach(badge => {
            keywords.push(badge.textContent.trim());
        });
        return keywords;
    }
    
    // 设置表单中的关键词
    function setKeywords(container, keywords) {
        container.innerHTML = '';
        if (keywords && keywords.length > 0) {
            keywords.forEach(keyword => {
                const badge = document.createElement('span');
                badge.className = 'keyword-badge';
                badge.innerHTML = `
                    ${keyword}
                    <span class="remove-keyword">
                        <i class="fas fa-times"></i>
                    </span>
                `;
                container.appendChild(badge);
                
                badge.querySelector('.remove-keyword').addEventListener('click', function() {
                    this.parentNode.remove();
                });
            });
        }
    }
    
    // 创建规则
    function createRule(formData) {
        const csrfToken = getCsrfToken();
        
        fetch('/api/agent-rules/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('创建规则失败');
            }
            return response.json();
        })
        .then(data => {
            showToast('success', '规则创建成功');
            loadRules();
            
            // 重置表单并关闭模态框
            if (createRuleForm) {
                createRuleForm.reset();
                keywordsContainer.innerHTML = '';
                contextKeywordsContainer.innerHTML = '';
                const modal = bootstrap.Modal.getInstance(document.getElementById('createRuleModal'));
                if (modal) modal.hide();
            }
        })
        .catch(error => {
            console.error('创建规则错误:', error);
            showToast('error', '创建规则失败');
        });
    }
    
    // 编辑规则
    function editRule(ruleId) {
        fetch(`/api/agent-rules/${ruleId}/`)
            .then(response => response.json())
            .then(rule => {
                // 填充编辑表单
                if (editRuleForm) {
                    editRuleForm.querySelector('#editRuleId').value = rule.id;
                    editRuleForm.querySelector('#editRuleName').value = rule.name;
                    editRuleForm.querySelector('#editResponse').value = rule.response;
                    editRuleForm.querySelector('#editPriority').value = rule.priority;
                    editRuleForm.querySelector('#editIsActive').checked = rule.is_active;
                    editRuleForm.querySelector('#editScope').value = rule.scope;
                    
                    // 设置关键词
                    setKeywords(editKeywordsContainer, rule.keywords);
                    setKeywords(editContextKeywordsContainer, rule.context_keywords);
                    
                    // 显示模态框
                    const modal = new bootstrap.Modal(document.getElementById('editRuleModal'));
                    modal.show();
                }
            })
            .catch(error => {
                console.error('获取规则详情失败:', error);
                showToast('error', '获取规则详情失败');
            });
    }
    
    // 更新规则
    function updateRule(formData) {
        const ruleId = formData.id;
        const csrfToken = getCsrfToken();
        
        fetch(`/api/agent-rules/${ruleId}/`, {
            method: 'PUT',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('更新规则失败');
            }
            return response.json();
        })
        .then(data => {
            showToast('success', '规则更新成功');
            loadRules();
            
            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('editRuleModal'));
            if (modal) modal.hide();
        })
        .catch(error => {
            console.error('更新规则错误:', error);
            showToast('error', '更新规则失败');
        });
    }
    
    // 删除规则
    function deleteRule(ruleId) {
        const csrfToken = getCsrfToken();
        
        fetch(`/api/agent-rules/${ruleId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('删除规则失败');
            }
            
            showToast('success', '规则删除成功');
            loadRules();
            
            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('deleteRuleModal'));
            if (modal) modal.hide();
        })
        .catch(error => {
            console.error('删除规则错误:', error);
            showToast('error', '删除规则失败');
        });
    }
    
    // 测试规则
    function testRule(ruleId, message) {
        const csrfToken = getCsrfToken();
        
        fetch(`/api/agent-rules/${ruleId}/test/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message })
        })
        .then(response => response.json())
        .then(data => {
            displayTestResult(data);
        })
        .catch(error => {
            console.error('测试规则失败:', error);
            showToast('error', '测试规则失败');
            if (testResultContent) {
                testResultContent.innerHTML = '<span class="test-result-error">测试失败: ' + error.message + '</span>';
            }
        });
    }
    
    // 显示测试结果
    function displayTestResult(result) {
        if (!testResultContent) return;
        
        if (result.matches) {
            testResultContent.innerHTML = `
                <div class="test-result-match">
                    <i class="fas fa-check-circle me-2"></i>匹配成功
                </div>
                <div class="mt-2">
                    <strong>匹配关键词:</strong> ${result.matched_keywords.join(', ') || '无'}
                </div>
                <div class="mt-2">
                    <strong>匹配上下文:</strong> ${result.matched_context_keywords.join(', ') || '无'}
                </div>
                <div class="mt-3">
                    <strong>响应结果:</strong>
                    <pre>${result.response}</pre>
                </div>
            `;
        } else {
            testResultContent.innerHTML = `
                <div class="test-result-no-match">
                    <i class="fas fa-times-circle me-2"></i>未匹配
                </div>
                <div class="mt-2">
                    <p>输入的消息与该规则不匹配。</p>
                </div>
            `;
        }
    }
    
    // 显示删除确认模态框
    function showDeleteModal(ruleId, ruleName) {
        if (!deleteRuleModal) return;
        
        const confirmMessage = deleteRuleModal.querySelector('#deleteRuleMessage');
        if (confirmMessage) {
            confirmMessage.textContent = `确定要删除规则 "${ruleName}" 吗？此操作不可恢复。`;
        }
        
        const confirmBtn = deleteRuleModal.querySelector('#confirmDeleteRule');
        if (confirmBtn) {
            confirmBtn.setAttribute('data-rule-id', ruleId);
            
            // 移除旧的事件监听器
            const newConfirmBtn = confirmBtn.cloneNode(true);
            confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
            
            // 添加新的事件监听器
            newConfirmBtn.addEventListener('click', function() {
                const ruleId = this.getAttribute('data-rule-id');
                deleteRule(ruleId);
            });
        }
        
        const modal = new bootstrap.Modal(deleteRuleModal);
        modal.show();
    }
    
    // 显示测试模态框
    function showTestModal(ruleId) {
        if (!testRuleForm) return;
        
        testRuleForm.querySelector('#testRuleId').value = ruleId;
        if (testResultContent) {
            testResultContent.innerHTML = '';
        }
        
        const modal = new bootstrap.Modal(document.getElementById('testRuleModal'));
        modal.show();
    }
    
    // 显示Toast通知
    function showToast(type, message) {
        const toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) return;
        
        const toast = document.createElement('div');
        toast.className = `toast fade-in`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        let bgClass = 'bg-primary';
        let icon = 'info-circle';
        
        switch(type) {
            case 'success':
                bgClass = 'bg-success';
                icon = 'check-circle';
                break;
            case 'error':
                bgClass = 'bg-danger';
                icon = 'exclamation-circle';
                break;
            case 'warning':
                bgClass = 'bg-warning';
                icon = 'exclamation-triangle';
                break;
        }
        
        toast.innerHTML = `
            <div class="toast-header ${bgClass} text-white">
                <i class="fas fa-${icon} me-2"></i>
                <strong class="me-auto">通知</strong>
                <small>刚刚</small>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast, {
            delay: 3000
        });
        
        bsToast.show();
        
        // 自动移除
        toast.addEventListener('hidden.bs.toast', function() {
            this.remove();
        });
    }
    
    // 表单提交事件
    if (createRuleForm) {
        createRuleForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = {
                name: this.querySelector('#ruleName').value,
                keywords: getKeywordsFromContainer(keywordsContainer),
                context_keywords: getKeywordsFromContainer(contextKeywordsContainer),
                response: this.querySelector('#response').value,
                priority: this.querySelector('#priority').value,
                is_active: this.querySelector('#isActive').checked,
                scope: this.querySelector('#scope').value
            };
            
            createRule(formData);
        });
    }
    
    if (editRuleForm) {
        editRuleForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = {
                id: this.querySelector('#editRuleId').value,
                name: this.querySelector('#editRuleName').value,
                keywords: getKeywordsFromContainer(editKeywordsContainer),
                context_keywords: getKeywordsFromContainer(editContextKeywordsContainer),
                response: this.querySelector('#editResponse').value,
                priority: this.querySelector('#editPriority').value,
                is_active: this.querySelector('#editIsActive').checked,
                scope: this.querySelector('#editScope').value
            };
            
            updateRule(formData);
        });
    }
    
    if (testRuleForm) {
        testRuleForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const ruleId = this.querySelector('#testRuleId').value;
            const message = this.querySelector('#testMessage').value;
            
            testRule(ruleId, message);
        });
    }
    
    // 初始化
    setupKeywordInputs();
    loadRules();
}); 