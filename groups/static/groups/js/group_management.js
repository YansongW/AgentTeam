/**
 * 群组管理页面JavaScript
 */

// 设置axios默认headers，包含CSRF令牌
function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue;
}

axios.defaults.headers.common['X-CSRFToken'] = getCSRFToken();

// 获取用户的Token
const token = localStorage.getItem('access_token');
if (token) {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
} else {
    // 如果没有登录，跳转到登录页面
    // window.location.href = '/api/users/login/';
}

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 加载我的群组
    loadMyGroups();
    
    // 添加Tab切换事件监听
    document.querySelectorAll('#groupTabs .nav-link').forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(event) {
            const targetId = event.target.getAttribute('data-bs-target');
            if (targetId === '#my-groups') {
                loadMyGroups();
            } else if (targetId === '#joined-groups') {
                loadJoinedGroups();
            } else if (targetId === '#public-groups') {
                loadPublicGroups();
            }
        });
    });
    
    // 加载代理列表
    loadAgents();
    
    // 创建群组按钮点击事件
    document.getElementById('createGroupBtn').addEventListener('click', createGroup);
});

// 加载我的群组
function loadMyGroups() {
    const container = document.getElementById('my-groups-container');
    container.innerHTML = '<div class="col-12 text-center py-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">加载中...</span></div></div>';
    
    axios.get('/api/groups/groups/?is_owner=true')
        .then(response => {
            if (response.data.length > 0) {
                container.innerHTML = '';
                response.data.forEach(group => {
                    container.appendChild(createGroupCard(group));
                });
            } else {
                container.innerHTML = '<div class="col-12 text-center py-5"><div class="alert alert-info">您还没有创建任何群组。点击右上角"创建新群组"按钮开始创建。</div></div>';
            }
        })
        .catch(error => {
            console.error('加载我的群组失败:', error);
            container.innerHTML = '<div class="col-12 text-center py-5"><div class="alert alert-danger">加载群组失败，请稍后重试。</div></div>';
        });
}

// 加载加入的群组
function loadJoinedGroups() {
    const container = document.getElementById('joined-groups-container');
    container.innerHTML = '<div class="col-12 text-center py-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">加载中...</span></div></div>';
    
    axios.get('/api/groups/groups/?is_member=true&is_owner=false')
        .then(response => {
            if (response.data.length > 0) {
                container.innerHTML = '';
                response.data.forEach(group => {
                    container.appendChild(createGroupCard(group));
                });
            } else {
                container.innerHTML = '<div class="col-12 text-center py-5"><div class="alert alert-info">您还没有加入任何群组。</div></div>';
            }
        })
        .catch(error => {
            console.error('加载加入的群组失败:', error);
            container.innerHTML = '<div class="col-12 text-center py-5"><div class="alert alert-danger">加载群组失败，请稍后重试。</div></div>';
        });
}

// 加载公开群组
function loadPublicGroups() {
    const container = document.getElementById('public-groups-container');
    container.innerHTML = '<div class="col-12 text-center py-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">加载中...</span></div></div>';
    
    axios.get('/api/groups/groups/?is_public=true&not_member=true')
        .then(response => {
            if (response.data.length > 0) {
                container.innerHTML = '';
                response.data.forEach(group => {
                    container.appendChild(createGroupCard(group, true));
                });
            } else {
                container.innerHTML = '<div class="col-12 text-center py-5"><div class="alert alert-info">没有可加入的公开群组。</div></div>';
            }
        })
        .catch(error => {
            console.error('加载公开群组失败:', error);
            container.innerHTML = '<div class="col-12 text-center py-5"><div class="alert alert-danger">加载群组失败，请稍后重试。</div></div>';
        });
}

// 创建群组卡片
function createGroupCard(group, isPublic = false) {
    const col = document.createElement('div');
    col.className = 'col-md-6 col-xl-4 mb-4';
    
    let joinButton = '';
    if (isPublic) {
        joinButton = `<button class="btn btn-outline-primary btn-sm join-group-btn" data-group-id="${group.id}">加入群组</button>`;
    }
    
    col.innerHTML = `
        <div class="card group-card h-100">
            <div class="card-body">
                <h5 class="card-title">${group.name}</h5>
                <p class="card-text text-muted">${group.description || '无描述'}</p>
                <div class="d-flex justify-content-between align-items-end">
                    <div>
                        <small class="text-muted">成员: ${group.member_count || 0}</small>
                        <div class="mt-2">
                            ${group.is_public ? '<span class="badge bg-success">公开</span>' : '<span class="badge bg-secondary">私有</span>'}
                        </div>
                    </div>
                    <div>
                        ${joinButton}
                        <button class="btn btn-primary btn-sm view-group-btn" data-group-id="${group.id}">查看详情</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 添加事件监听器
    setTimeout(() => {
        const viewBtn = col.querySelector('.view-group-btn');
        viewBtn.addEventListener('click', () => {
            loadGroupDetail(group.id);
        });
        
        const joinBtn = col.querySelector('.join-group-btn');
        if (joinBtn) {
            joinBtn.addEventListener('click', () => {
                joinGroup(group.id);
            });
        }
    }, 0);
    
    return col;
}

// 加载群组详情
function loadGroupDetail(groupId) {
    const modal = new bootstrap.Modal(document.getElementById('groupDetailModal'));
    modal.show();
    
    const contentDiv = document.getElementById('groupDetailContent');
    contentDiv.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">加载中...</span></div></div>';
    
    // 设置聊天按钮链接
    const chatBtn = document.getElementById('openChatBtn');
    chatBtn.href = `/websocket-test/websocket-test/?room=${groupId}`;
    
    axios.get(`/api/groups/groups/${groupId}/`)
        .then(response => {
            const group = response.data;
            
            let membersHtml = '';
            if (group.members && group.members.length > 0) {
                membersHtml = '<div class="mt-4"><h6>群组成员</h6><div class="row">';
                group.members.forEach(member => {
                    const isAgent = member.agent !== null;
                    const name = isAgent ? member.agent_name : member.user_name;
                    const badge = isAgent ? 'agent-badge' : '';
                    
                    membersHtml += `
                        <div class="col-6 col-md-4 col-lg-3 mb-3">
                            <div class="d-flex align-items-center">
                                <div class="position-relative me-2">
                                    <img src="/static/images/${isAgent ? 'agent' : 'user'}_avatar.png" class="member-avatar" alt="${name}">
                                    <div class="member-badge ${badge}"></div>
                                </div>
                                <div>
                                    <div class="fw-bold">${name}</div>
                                    <small class="text-muted">${member.role}</small>
                                </div>
                            </div>
                        </div>
                    `;
                });
                membersHtml += '</div></div>';
            }
            
            let rulesHtml = '';
            if (group.rules && group.rules.length > 0) {
                rulesHtml = '<div class="mt-4"><h6>群组规则</h6><div class="list-group rules-list">';
                group.rules.forEach(rule => {
                    rulesHtml += `
                        <div class="list-group-item">
                            <div class="d-flex justify-content-between">
                                <h6 class="mb-1">${rule.name}</h6>
                                <span class="badge ${rule.is_active ? 'bg-success' : 'bg-secondary'}">${rule.is_active ? '已启用' : '已禁用'}</span>
                            </div>
                            <p class="mb-1 small">${rule.description || '无描述'}</p>
                            <small class="text-muted">优先级: ${rule.priority}, 触发条件: ${rule.trigger_type_display}</small>
                        </div>
                    `;
                });
                rulesHtml += '</div></div>';
            }
            
            contentDiv.innerHTML = `
                <div class="row">
                    <div class="col-md-8">
                        <h4>${group.name}</h4>
                        <p>${group.description || '无描述'}</p>
                        <div class="mt-3">
                            <span class="badge ${group.is_public ? 'bg-success' : 'bg-secondary'} me-2">${group.is_public ? '公开' : '私有'}</span>
                            <small class="text-muted">创建于: ${new Date(group.created_at).toLocaleString()}</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body">
                                <h6 class="card-title">群组信息</h6>
                                <div class="mb-2">
                                    <small class="text-muted d-block">ID: ${group.id}</small>
                                    <small class="text-muted d-block">成员数: ${group.member_count || 0}</small>
                                    <small class="text-muted d-block">拥有者: ${group.owner_name}</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                ${membersHtml}
                ${rulesHtml}
            `;
            
            // 根据用户权限显示/隐藏编辑按钮
            const editBtn = document.getElementById('editGroupBtn');
            if (group.is_owner) {
                editBtn.style.display = 'block';
                editBtn.setAttribute('data-group-id', group.id);
                editBtn.onclick = () => {
                    // 跳转到编辑页面或显示编辑模态框
                    alert('编辑功能尚未实现');
                };
            } else {
                editBtn.style.display = 'none';
            }
        })
        .catch(error => {
            console.error('加载群组详情失败:', error);
            contentDiv.innerHTML = '<div class="alert alert-danger">加载群组详情失败，请稍后重试。</div>';
        });
}

// 加载代理列表
function loadAgents() {
    const container = document.getElementById('agentsSelector');
    
    axios.get('/api/agents/agents/')
        .then(response => {
            if (response.data.length > 0) {
                container.innerHTML = '';
                response.data.forEach(agent => {
                    const col = document.createElement('div');
                    col.className = 'col-md-6 col-xl-4 mb-3';
                    col.innerHTML = `
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" name="agents" id="agent${agent.id}" value="${agent.id}">
                            <label class="form-check-label" for="agent${agent.id}">
                                ${agent.name}
                                <small class="d-block text-muted">${agent.role_display}</small>
                            </label>
                        </div>
                    `;
                    container.appendChild(col);
                });
            } else {
                container.innerHTML = '<div class="col-12"><div class="alert alert-info">您还没有创建任何代理。</div></div>';
            }
        })
        .catch(error => {
            console.error('加载代理列表失败:', error);
            container.innerHTML = '<div class="col-12"><div class="alert alert-danger">加载代理列表失败，请稍后重试。</div></div>';
        });
}

// 创建群组
function createGroup() {
    const form = document.getElementById('createGroupForm');
    const formData = new FormData(form);
    
    const data = {
        name: formData.get('name'),
        description: formData.get('description'),
        is_public: formData.get('is_public') === 'on',
    };
    
    // 获取选中的代理
    const selectedAgents = [];
    document.querySelectorAll('input[name="agents"]:checked').forEach(checkbox => {
        selectedAgents.push(checkbox.value);
    });
    
    if (selectedAgents.length > 0) {
        data.agents = selectedAgents;
    }
    
    // 创建群组
    axios.post('/api/groups/groups/', data)
        .then(response => {
            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('createGroupModal'));
            modal.hide();
            
            // 重新加载我的群组
            loadMyGroups();
            
            // 重置表单
            form.reset();
            
            alert('群组创建成功！');
        })
        .catch(error => {
            console.error('创建群组失败:', error);
            alert('创建群组失败，请检查输入并重试。');
        });
}

// 加入群组
function joinGroup(groupId) {
    axios.post(`/api/groups/groups/${groupId}/join/`)
        .then(response => {
            alert('成功加入群组！');
            // 重新加载公开群组和加入的群组
            loadPublicGroups();
            loadJoinedGroups();
        })
        .catch(error => {
            console.error('加入群组失败:', error);
            alert('加入群组失败，请稍后重试。');
        });
} 