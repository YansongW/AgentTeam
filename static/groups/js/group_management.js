// 生成群组卡片HTML
function createGroupCard(group) {
    const isOwner = group.owner.id === currentUser.id;
    
    const avatarHtml = group.avatar ? 
        `<img src="${group.avatar}" alt="${group.name}" class="img-fluid rounded">` : 
        `<div class="default-avatar">${group.name.charAt(0)}</div>`;
    
    const publicBadge = group.is_public ? 
        '<span class="badge bg-success me-2">公开</span>' : 
        '<span class="badge bg-secondary me-2">私有</span>';
    
    const ownerActions = isOwner ? 
        `<button class="btn btn-outline-primary btn-sm edit-group-btn" data-group-id="${group.id}">
            <i class="bi bi-pencil"></i> 编辑
        </button>
        <button class="btn btn-outline-danger btn-sm delete-group-btn" data-group-id="${group.id}">
            <i class="bi bi-trash"></i> 删除
        </button>` : '';
    
    return `
    <div class="col-md-6 col-lg-4 mb-4">
        <div class="card group-card h-100">
            <div class="card-body">
                <div class="d-flex align-items-center">
                    <div class="group-avatar me-3">
                        ${avatarHtml}
                    </div>
                    <div class="flex-grow-1">
                        <h5 class="card-title mb-1">${group.name}</h5>
                        <p class="card-text text-muted small">${group.description || '无描述'}</p>
                        <div class="d-flex align-items-center small flex-wrap">
                            <span class="badge bg-primary me-2">${group.member_count} 成员</span>
                            ${publicBadge}
                            <span class="text-muted">创建于: ${new Date(group.created_at).toLocaleDateString()}</span>
                        </div>
                    </div>
                </div>
                <div class="card-actions mt-3">
                    <a href="/groups/chat/${group.id}/" class="btn btn-primary btn-sm">
                        <i class="bi bi-chat-dots"></i> 进入群聊
                    </a>
                    ${ownerActions}
                    ${!isOwner ? `<button class="btn btn-outline-danger btn-sm leave-group-btn" data-group-id="${group.id}">
                        <i class="bi bi-box-arrow-left"></i> 退出
                    </button>` : ''}
                    ${!isOwner && !group.is_member ? `<button class="btn btn-outline-success btn-sm join-group-btn" data-group-id="${group.id}">
                        <i class="bi bi-plus-circle"></i> 加入
                    </button>` : ''}
                </div>
            </div>
        </div>
    </div>`;
} 