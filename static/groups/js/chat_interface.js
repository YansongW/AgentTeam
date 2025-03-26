// 群聊页面WebSocket连接及消息处理
document.addEventListener('DOMContentLoaded', function() {
    // 主要DOM元素
    const messagesContainer = document.getElementById('messagesContainer');
    const messagesList = document.getElementById('messagesList');
    const messageInput = document.getElementById('messageInput');
    const messageForm = document.getElementById('messageForm');
    const typingStatus = document.getElementById('typingStatus');
    const membersList = document.getElementById('membersList');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const mentionMenu = document.getElementById('mentionMenu');
    const attachmentBtn = document.getElementById('attachmentBtn');
    const attachmentInput = document.getElementById('attachmentInput');
    const attachmentPreview = document.getElementById('attachmentPreview');
    const emojiBtn = document.getElementById('emojiBtn');
    const showAllMembers = document.getElementById('showAllMembers');
    const showOnlineMembers = document.getElementById('showOnlineMembers');
    const memberCount = document.getElementById('memberCount');
    const mobileOnlineCount = document.getElementById('mobileOnlineCount');
    const imageViewerModal = new bootstrap.Modal(document.getElementById('imageViewerModal'));
    const modalImage = document.getElementById('modalImage');
    const downloadImageBtn = document.getElementById('downloadImageBtn');

    // 获取URL参数中的群组ID
    const urlParams = new URLSearchParams(window.location.search);
    const groupId = urlParams.get('id');
    
    // WebSocket连接
    let socket = null;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    const reconnectDelay = 3000;
    
    // 用户和消息相关数据
    let currentUser = null;
    let groupMembers = [];
    let typingTimer = null;
    let lastMessageId = null;
    let isLoadingHistory = false;
    let noMoreHistory = false;
    let attachment = null;
    
    // 初始化函数
    function init() {
        // 获取当前用户信息
        fetchCurrentUser()
            .then(user => {
                currentUser = user;
                // 初始化WebSocket连接
                initWebSocket();
                // 加载群组信息和成员
                loadGroupInfo();
                loadGroupMembers();
                // 加载历史消息
                loadHistoryMessages();
            })
            .catch(error => {
                showErrorMessage('无法获取用户信息，请刷新页面重试');
                console.error('Failed to fetch current user:', error);
            });
        
        // 初始化事件监听器
        initEventListeners();
    }
    
    // 初始化WebSocket连接
    function initWebSocket() {
        // 确保有groupId和currentUser
        if (!groupId || !currentUser) {
            showErrorMessage('初始化WebSocket失败：缺少必要参数');
            return;
        }
        
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/chat/${groupId}/?user_id=${currentUser.id}`;
        
        try {
            socket = new WebSocket(wsUrl);
            
            socket.onopen = function(e) {
                console.log('WebSocket连接已建立');
                reconnectAttempts = 0;
                // 发送上线通知
                sendStatusMessage('online');
            };
            
            socket.onmessage = function(e) {
                handleWebSocketMessage(e.data);
            };
            
            socket.onclose = function(e) {
                console.log('WebSocket连接已关闭', e.code, e.reason);
                if (e.code !== 1000) {
                    attemptReconnect();
                }
            };
            
            socket.onerror = function(e) {
                console.error('WebSocket连接错误', e);
                showErrorMessage('WebSocket连接错误，请刷新页面重试');
            };
        } catch (error) {
            console.error('初始化WebSocket失败', error);
            showErrorMessage('初始化WebSocket失败，请刷新页面重试');
        }
    }
    
    // 尝试重新连接WebSocket
    function attemptReconnect() {
        if (reconnectAttempts >= maxReconnectAttempts) {
            showErrorMessage('无法重新连接到服务器，请刷新页面');
            return;
        }
        
        reconnectAttempts++;
        setTimeout(() => {
            console.log(`尝试重新连接 (${reconnectAttempts}/${maxReconnectAttempts})...`);
            initWebSocket();
        }, reconnectDelay);
    }
    
    // 处理WebSocket消息
    function handleWebSocketMessage(data) {
        try {
            const message = JSON.parse(data);
            
            switch (message.type) {
                case 'chat_message':
                    displayMessage(message);
                    break;
                case 'system_message':
                    displaySystemMessage(message.content);
                    break;
                case 'user_joined':
                    handleUserJoined(message.user);
                    break;
                case 'user_left':
                    handleUserLeft(message.user_id);
                    break;
                case 'typing_status':
                    handleTypingStatus(message);
                    break;
                case 'members_update':
                    loadGroupMembers();
                    break;
                case 'error':
                    showErrorMessage(message.content);
                    break;
                default:
                    console.log('收到未知类型的消息', message);
            }
        } catch (error) {
            console.error('解析WebSocket消息失败', error, data);
        }
    }
    
    // 显示消息
    function displayMessage(message) {
        // 检查消息是否已存在（防止重复）
        if (document.getElementById(`message-${message.id}`)) {
            return;
        }
        
        const template = document.getElementById('messageTemplate');
        const messageNode = document.importNode(template.content, true).firstElementChild;
        
        // 设置消息ID和CSS类
        messageNode.id = `message-${message.id}`;
        
        // 根据消息类型和发送者添加CSS类
        if (message.sender.id === currentUser.id) {
            messageNode.classList.add('own-message');
        } else {
            messageNode.classList.add('other-message');
        }
        
        if (message.sender.is_agent) {
            messageNode.classList.add('agent-message');
        }
        
        // 添加特殊标记 - 代理响应消息
        if (message.type === 'agent_response') {
            messageNode.classList.add('agent-response');
            
            // 添加规则触发标记（如果存在）
            if (message.metadata && message.metadata.rule_name) {
                const badge = document.createElement('span');
                badge.className = 'badge bg-info rule-badge';
                badge.textContent = message.metadata.rule_name;
                messageNode.querySelector('.message-header').appendChild(badge);
            }
        }
        
        // 设置发送者头像
        const avatarElement = messageNode.querySelector('.sender-avatar img');
        if (message.sender.avatar) {
            avatarElement.src = message.sender.avatar;
        } else {
            // 如果没有头像，使用首字母作为替代
            avatarElement.parentElement.innerHTML = message.sender.username.charAt(0).toUpperCase();
        }
        
        // 设置发送者名称
        messageNode.querySelector('.message-sender').textContent = message.sender.username;
        
        // 设置消息时间
        const messageTime = new Date(message.timestamp);
        messageNode.querySelector('.message-time').textContent = messageTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        
        // 设置消息内容
        const contentElement = messageNode.querySelector('.message-content');
        
        // 处理不同类型的消息内容
        if (message.content_type === 'text') {
            // 处理文本中的提及、表情和markdown
            const sanitizedContent = DOMPurify.sanitize(marked.parse(message.content));
            contentElement.innerHTML = processMentions(sanitizedContent);
        } else if (message.content_type === 'image') {
            const imgElement = document.createElement('img');
            imgElement.src = message.content;
            imgElement.alt = 'Image';
            imgElement.classList.add('img-fluid', 'rounded');
            imgElement.style.maxHeight = '200px';
            imgElement.style.cursor = 'pointer';
            
            imgElement.addEventListener('click', function() {
                modalImage.src = message.content;
                downloadImageBtn.href = message.content;
                imageViewerModal.show();
            });
            
            contentElement.appendChild(imgElement);
        } else if (message.content_type === 'file') {
            const fileInfo = JSON.parse(message.content);
            
            const fileAttachment = document.createElement('div');
            fileAttachment.className = 'file-attachment';
            
            // 根据文件类型选择图标
            const fileIcon = getFileIcon(fileInfo.mime_type);
            
            fileAttachment.innerHTML = `
                <i class="bi ${fileIcon} file-icon"></i>
                <div>
                    <div>${fileInfo.name}</div>
                    <small class="text-muted">${formatFileSize(fileInfo.size)}</small>
                </div>
                <a href="${fileInfo.url}" class="btn btn-sm btn-outline-primary ms-auto" download>
                    <i class="bi bi-download"></i>
                </a>
            `;
            
            contentElement.appendChild(fileAttachment);
        }
        
        // 如果消息有回复的消息ID，显示引用
        if (message.reply_to || (message.payload && message.payload.reply_to)) {
            const replyToId = message.reply_to || message.payload.reply_to;
            const replyToElement = document.getElementById(`message-${replyToId}`);
            
            if (replyToElement) {
                const replyPreview = document.createElement('div');
                replyPreview.className = 'reply-preview';
                
                const replyContent = replyToElement.querySelector('.message-content').textContent;
                const replySender = replyToElement.querySelector('.message-sender').textContent;
                
                replyPreview.innerHTML = `
                    <div class="reply-info">回复 ${replySender}</div>
                    <div class="reply-text">${replyContent.substring(0, 50)}${replyContent.length > 50 ? '...' : ''}</div>
                `;
                
                // 在内容前面插入引用
                contentElement.parentElement.insertBefore(replyPreview, contentElement);
                
                // 点击引用时滚动到原消息
                replyPreview.addEventListener('click', () => {
                    replyToElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    replyToElement.classList.add('highlight');
                    setTimeout(() => {
                        replyToElement.classList.remove('highlight');
                    }, 2000);
                });
            }
        }
        
        // 添加到消息列表
        messagesList.appendChild(messageNode);
        
        // 滚动到最新消息
        scrollToBottom();
        
        // 更新最后消息ID，用于加载历史消息
        lastMessageId = message.id;
    }
    
    // 显示系统消息
    function displaySystemMessage(content) {
        const systemMessage = document.createElement('div');
        systemMessage.className = 'message system-message';
        systemMessage.textContent = content;
        messagesList.appendChild(systemMessage);
        scrollToBottom();
    }
    
    // 显示错误消息
    function showErrorMessage(content) {
        const errorMessage = document.createElement('div');
        errorMessage.className = 'message error-message';
        errorMessage.textContent = content;
        messagesList.appendChild(errorMessage);
        scrollToBottom();
    }
    
    // 处理用户加入
    function handleUserJoined(user) {
        displaySystemMessage(`${user.username} 加入了群聊`);
        loadGroupMembers();
    }
    
    // 处理用户离开
    function handleUserLeft(userId) {
        const member = groupMembers.find(m => m.user.id === userId);
        if (member) {
            displaySystemMessage(`${member.user.username} 离开了群聊`);
        } else {
            displaySystemMessage(`一位成员离开了群聊`);
        }
        loadGroupMembers();
    }
    
    // 处理输入状态
    function handleTypingStatus(message) {
        if (message.user.id === currentUser.id) {
            return; // 不显示自己的输入状态
        }
        
        const typingText = document.getElementById('typingText');
        typingText.textContent = `${message.user.username} 正在输入...`;
        
        if (message.is_typing) {
            typingStatus.classList.remove('d-none');
            
            // 5秒后自动隐藏
            clearTimeout(typingTimer);
            typingTimer = setTimeout(() => {
                typingStatus.classList.add('d-none');
            }, 5000);
        } else {
            typingStatus.classList.add('d-none');
        }
    }
    
    // 发送用户状态信息
    function sendStatusMessage(status) {
        if (socket && socket.readyState === WebSocket.OPEN) {
            const statusMessage = {
                type: 'status',
                status: status
            };
            socket.send(JSON.stringify(statusMessage));
        }
    }
    
    // 发送输入状态
    function sendTypingStatus(isTyping) {
        if (socket && socket.readyState === WebSocket.OPEN) {
            const typingMessage = {
                type: 'typing',
                is_typing: isTyping
            };
            socket.send(JSON.stringify(typingMessage));
        }
    }
    
    // 发送消息
    function sendMessage(content, contentType = 'text') {
        if (!content.trim() && contentType === 'text') {
            return; // 不发送空消息
        }
        
        if (socket && socket.readyState === WebSocket.OPEN) {
            // 构建消息对象
            const messageData = {
                type: 'message',
                content: content,
                content_type: contentType
            };
            
            // 添加回复ID（如果有）
            if (messageInput.dataset.replyTo) {
                messageData.reply_to = messageInput.dataset.replyTo;
                
                // 清除回复预览
                const replyPreview = document.querySelector('.reply-preview-input');
                if (replyPreview) {
                    replyPreview.remove();
                }
                delete messageInput.dataset.replyTo;
            }
            
            // 发送消息
            socket.send(JSON.stringify(messageData));
            
            // 清除输入框和附件
            if (contentType === 'text') {
                messageInput.value = '';
                messageInput.style.height = 'auto';
                messageInput.focus();
            }
            
            if (attachment) {
                clearAttachment();
            }
        } else {
            showErrorMessage('消息发送失败，请检查网络连接');
        }
    }
    
    // 加载群组信息
    function loadGroupInfo() {
        fetch(`/api/groups/${groupId}/`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('无法获取群组信息');
                }
                return response.json();
            })
            .then(group => {
                // 更新群组信息可以在这里完成
                console.log('群组信息加载成功', group);
            })
            .catch(error => {
                console.error('加载群组信息失败', error);
                showErrorMessage('无法加载群组信息');
            });
    }
    
    // 加载群组成员
    function loadGroupMembers() {
        fetch(`/api/groups/${groupId}/members/`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('无法获取群组成员');
                }
                return response.json();
            })
            .then(members => {
                groupMembers = members;
                renderMembersList(members);
                updateMemberCount(members);
            })
            .catch(error => {
                console.error('加载群组成员失败', error);
                showErrorMessage('无法加载群组成员');
            });
    }
    
    // 渲染成员列表
    function renderMembersList(members, filterOnline = false) {
        membersList.innerHTML = '';
        
        // 如果筛选在线成员，只显示在线的
        const filteredMembers = filterOnline 
            ? members.filter(member => member.online_status === 'online')
            : members;
        
        // 先显示在线用户，然后显示代理，最后显示离线用户
        const sortedMembers = [...filteredMembers].sort((a, b) => {
            // 优先级：在线状态 > 代理 > 名称
            if (a.online_status === 'online' && b.online_status !== 'online') return -1;
            if (a.online_status !== 'online' && b.online_status === 'online') return 1;
            if (a.user.is_agent && !b.user.is_agent) return -1;
            if (!a.user.is_agent && b.user.is_agent) return 1;
            return a.user.username.localeCompare(b.user.username);
        });
        
        if (sortedMembers.length === 0) {
            const emptyElement = document.createElement('div');
            emptyElement.className = 'text-center text-muted py-3';
            emptyElement.textContent = filterOnline ? '没有在线成员' : '没有成员';
            membersList.appendChild(emptyElement);
            return;
        }
        
        sortedMembers.forEach(member => {
            const memberItem = document.createElement('div');
            memberItem.className = 'member-item';
            memberItem.dataset.userId = member.user.id;
            
            // 状态颜色
            let statusClass = 'offline';
            if (member.online_status === 'online') {
                statusClass = 'online';
            } else if (member.online_status === 'busy') {
                statusClass = 'busy';
            }
            
            // 角色标签
            let roleClass = 'member';
            let roleText = '成员';
            if (member.role === 'admin') {
                roleClass = 'admin';
                roleText = '管理员';
            } else if (member.role === 'owner') {
                roleClass = 'admin';
                roleText = '所有者';
            }
            
            // 头像
            let avatarHtml = '';
            if (member.user.avatar) {
                avatarHtml = `<img src="${member.user.avatar}" alt="${member.user.username}" class="member-avatar">`;
            } else {
                avatarHtml = `
                    <div class="member-avatar bg-secondary text-white d-flex align-items-center justify-content-center">
                        ${member.user.username.charAt(0).toUpperCase()}
                    </div>
                `;
            }
            
            // 成员类型标识
            const memberType = member.user.is_agent ? 
                '<span class="badge bg-info">代理</span>' : '';
            
            memberItem.innerHTML = `
                ${avatarHtml}
                <span class="member-name">${member.user.username}</span>
                ${memberType}
                <span class="member-status ${statusClass}"></span>
                <span class="member-role ${roleClass}">${roleText}</span>
            `;
            
            // 添加点击事件，插入@提及
            memberItem.addEventListener('click', () => {
                insertMention(member.user);
            });
            
            membersList.appendChild(memberItem);
        });
    }
    
    // 更新成员数量
    function updateMemberCount(members) {
        const totalCount = members.length;
        const onlineCount = members.filter(m => m.online_status === 'online').length;
        const agentCount = members.filter(m => m.user.is_agent).length;
        
        memberCount.textContent = `${onlineCount}/${totalCount} 在线 · ${agentCount} 代理`;
        mobileOnlineCount.textContent = `${onlineCount}/${totalCount} 在线`;
    }
    
    // 加载历史消息
    function loadHistoryMessages(before = null) {
        if (isLoadingHistory || noMoreHistory) return;
        
        isLoadingHistory = true;
        
        let url = `/api/groups/${groupId}/messages/?limit=20`;
        if (before) {
            url += `&before=${before}`;
        }
        
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error('无法获取历史消息');
                }
                return response.json();
            })
            .then(data => {
                // 移除加载指示器
                const loadingIndicator = messagesList.querySelector('.system-message');
                if (loadingIndicator) {
                    loadingIndicator.remove();
                }
                
                if (data.results.length === 0) {
                    noMoreHistory = true;
                    displaySystemMessage('没有更多历史消息');
                    return;
                }
                
                // 保存第一条消息的引用，用于计算滚动位置
                const firstMessage = messagesList.firstChild;
                const firstMessageOffset = firstMessage ? firstMessage.offsetTop : 0;
                
                // 显示消息（反向，最早的在前面）
                const reversedMessages = [...data.results].reverse();
                
                // 添加到顶部
                for (const message of reversedMessages) {
                    displayMessage(message);
                    lastMessageId = message.id;
                }
                
                // 如果是首次加载，滚动到底部
                if (!before) {
                    scrollToBottom();
                } else {
                    // 如果是加载更早的消息，保持滚动位置
                    const newFirstMessage = messagesList.firstChild;
                    const newOffset = newFirstMessage.offsetTop;
                    messagesContainer.scrollTop = newOffset - firstMessageOffset;
                }
            })
            .catch(error => {
                console.error('加载历史消息失败', error);
                showErrorMessage('无法加载历史消息');
            })
            .finally(() => {
                isLoadingHistory = false;
            });
    }
    
    // 获取当前用户信息
    function fetchCurrentUser() {
        return fetch('/api/users/current/')
            .then(response => {
                if (!response.ok) {
                    throw new Error('无法获取当前用户信息');
                }
                return response.json();
            });
    }
    
    // 初始化事件监听器
    function initEventListeners() {
        // 监听消息表单提交
        messageForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const messageText = messageInput.value.trim();
            if (messageText) {
                sendMessage(messageText);
            }
        });
        
        // 监听输入框内容变化（处理正在输入状态）
        let typingTimeout = null;
        messageInput.addEventListener('input', function() {
            // 自动调整高度
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
            
            // 发送正在输入状态
            if (!typingTimeout) {
                sendTypingStatus(true);
            }
            
            clearTimeout(typingTimeout);
            typingTimeout = setTimeout(() => {
                sendTypingStatus(false);
                typingTimeout = null;
            }, 2000);
            
            // 处理@提及
            handleMentionInput();
        });
        
        // 监听按键事件（处理提及菜单导航）
        messageInput.addEventListener('keydown', function(e) {
            // 监听@提及菜单导航
            if (mentionMenu.classList.contains('d-block')) {
                const activeItem = mentionMenu.querySelector('.mention-item.active');
                
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    if (activeItem) {
                        const nextItem = activeItem.nextElementSibling;
                        if (nextItem) {
                            activeItem.classList.remove('active');
                            nextItem.classList.add('active');
                            nextItem.scrollIntoView({ block: 'nearest' });
                        }
                    } else {
                        const firstItem = mentionMenu.querySelector('.mention-item');
                        if (firstItem) {
                            firstItem.classList.add('active');
                        }
                    }
                }
                
                else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    if (activeItem) {
                        const prevItem = activeItem.previousElementSibling;
                        if (prevItem) {
                            activeItem.classList.remove('active');
                            prevItem.classList.add('active');
                            prevItem.scrollIntoView({ block: 'nearest' });
                        }
                    } else {
                        const lastItem = mentionMenu.querySelector('.mention-item:last-child');
                        if (lastItem) {
                            lastItem.classList.add('active');
                        }
                    }
                }
                
                else if (e.key === 'Enter' || e.key === 'Tab') {
                    e.preventDefault();
                    if (activeItem) {
                        const userId = activeItem.getAttribute('data-id');
                        const userType = activeItem.getAttribute('data-type');
                        const username = activeItem.getAttribute('data-name');
                        insertMentionAtCursor(userId, userType, username);
                    }
                }
                
                else if (e.key === 'Escape') {
                    e.preventDefault();
                    mentionMenu.classList.remove('d-block');
                }
            }
            
            // 处理快捷键
            // Ctrl+Enter 发送消息
            if (e.key === 'Enter' && e.ctrlKey) {
                e.preventDefault();
                messageForm.dispatchEvent(new Event('submit'));
            }
            
            // 回复功能（按R键回复当前选中消息）
            if (e.key === 'r' && document.querySelector('.message.selected')) {
                e.preventDefault();
                const selectedMessage = document.querySelector('.message.selected');
                replyToMessage(selectedMessage.id.replace('message-', ''));
            }
        });
        
        // 监听点击空白处，关闭提及菜单
        document.addEventListener('click', function(e) {
            if (!mentionMenu.contains(e.target) && e.target !== messageInput) {
                mentionMenu.classList.remove('d-block');
            }
        });
        
        // 消息列表滚动到顶部时加载更多历史消息
        messagesContainer.addEventListener('scroll', function() {
            if (messagesContainer.scrollTop === 0 && !isLoadingHistory && !noMoreHistory) {
                loadHistoryMessages(lastMessageId);
                
                // 显示加载指示器
                const loadingIndicator = document.createElement('div');
                loadingIndicator.className = 'message system-message';
                loadingIndicator.innerHTML = `
                    <div class="spinner-border spinner-border-sm" role="status">
                        <span class="visually-hidden">加载中...</span>
                    </div>
                    <span class="ms-2">加载历史消息...</span>
                `;
                messagesList.insertBefore(loadingIndicator, messagesList.firstChild);
            }
        });
        
        // 侧边栏切换按钮
        sidebarToggle.addEventListener('click', function() {
            document.querySelector('.sidebar').classList.toggle('d-md-block');
            document.querySelector('.sidebar').classList.toggle('d-none');
        });
        
        // 成员列表过滤
        showAllMembers.addEventListener('click', function() {
            this.classList.add('active');
            showOnlineMembers.classList.remove('active');
            document.querySelectorAll('.member-item').forEach(el => {
                el.style.display = 'flex';
            });
        });
        
        showOnlineMembers.addEventListener('click', function() {
            this.classList.add('active');
            showAllMembers.classList.remove('active');
            document.querySelectorAll('.member-item').forEach(el => {
                if (!el.classList.contains('online')) {
                    el.style.display = 'none';
                } else {
                    el.style.display = 'flex';
                }
            });
        });
        
        // 附件按钮点击事件
        attachmentBtn.addEventListener('click', function() {
            attachmentInput.click();
        });
        
        // 附件选择变化事件
        attachmentInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                handleFileUpload(this.files[0]);
            }
        });
        
        // 消息点击事件（选择消息）
        messagesList.addEventListener('click', function(e) {
            // 处理消息选中
            const messageElement = e.target.closest('.message');
            if (messageElement) {
                // 如果之前有选中的消息，取消选中
                const previousSelected = document.querySelector('.message.selected');
                if (previousSelected) {
                    previousSelected.classList.remove('selected');
                }
                
                // 选中当前消息
                if (previousSelected !== messageElement) {
                    messageElement.classList.add('selected');
                }
            }
        });
        
        // 表情按钮点击事件（未实现，需要集成表情选择器）
        emojiBtn.addEventListener('click', function() {
            alert('表情功能即将推出，敬请期待！');
        });
        
        // 消息列表双击事件（回复消息）
        messagesList.addEventListener('dblclick', function(e) {
            const messageElement = e.target.closest('.message');
            if (messageElement) {
                const messageId = messageElement.id.replace('message-', '');
                replyToMessage(messageId);
            }
        });
    }
    
    // 处理@提及输入
    function handleMentionInput() {
        const text = messageInput.value;
        const cursorPos = messageInput.selectionStart;
        
        // 查找光标前的最后一个@符号位置
        let atIndex = -1;
        for (let i = cursorPos - 1; i >= 0; i--) {
            if (text[i] === '@') {
                atIndex = i;
                break;
            } else if (text[i] === ' ' || text[i] === '\n') {
                break;
            }
        }
        
        // 如果找到@，且在光标前
        if (atIndex !== -1 && atIndex < cursorPos) {
            const query = text.substring(atIndex + 1, cursorPos).toLowerCase();
            
            // 过滤成员列表
            const filteredMembers = groupMembers.filter(member => {
                const username = member.user.username.toLowerCase();
                return username.includes(query);
            });
            
            if (filteredMembers.length > 0) {
                showMentionMenu(filteredMembers, query);
            } else {
                mentionMenu.classList.remove('d-block');
            }
        } else {
            mentionMenu.classList.remove('d-block');
        }
    }
    
    // 显示@提及菜单
    function showMentionMenu(members, query) {
        // 清空原有内容
        mentionMenu.innerHTML = '';
        
        // 定位菜单
        positionMentionMenu();
        
        // 添加成员项
        members.slice(0, 10).forEach(member => {
            const memberItem = document.createElement('div');
            memberItem.className = 'mention-item';
            memberItem.setAttribute('data-id', member.user.id);
            memberItem.setAttribute('data-type', member.user.is_agent ? 'agent' : 'user');
            memberItem.setAttribute('data-name', member.user.username);
            
            if (member.user.is_agent) {
                memberItem.innerHTML = `
                    <span class="badge bg-success me-2">代理</span>
                    <span>${member.user.username}</span>
                `;
            } else {
                memberItem.innerHTML = `
                    <span>${member.user.username}</span>
                `;
            }
            
            // 点击插入提及
            memberItem.addEventListener('click', function() {
                const userId = this.getAttribute('data-id');
                const userType = this.getAttribute('data-type');
                const username = this.getAttribute('data-name');
                insertMentionAtCursor(userId, userType, username);
            });
            
            mentionMenu.appendChild(memberItem);
        });
        
        // 显示菜单
        mentionMenu.classList.add('d-block');
        
        // 默认选中第一项
        if (mentionMenu.children.length > 0) {
            mentionMenu.children[0].classList.add('active');
        }
    }
    
    // 定位@提及菜单
    function positionMentionMenu() {
        // 获取光标位置
        const cursorPosition = getCursorCoordinates(messageInput);
        
        // 设置菜单位置
        mentionMenu.style.top = (cursorPosition.top + 20) + 'px';
        mentionMenu.style.left = cursorPosition.left + 'px';
    }
    
    // 获取光标坐标
    function getCursorCoordinates(input) {
        // 创建一个临时元素计算位置
        const div = document.createElement('div');
        div.style.position = 'absolute';
        div.style.visibility = 'hidden';
        div.style.whiteSpace = 'pre-wrap';
        div.style.width = input.offsetWidth + 'px';
        div.style.font = window.getComputedStyle(input).font;
        div.style.padding = window.getComputedStyle(input).padding;
        
        // 获取光标前的文本
        const text = input.value.substring(0, input.selectionStart);
        div.textContent = text;
        
        // 添加一个临时元素标记光标位置
        const span = document.createElement('span');
        span.textContent = '|';
        div.appendChild(span);
        
        document.body.appendChild(div);
        const coordinates = {
            top: span.offsetTop + input.offsetTop,
            left: span.offsetLeft + input.offsetLeft
        };
        document.body.removeChild(div);
        
        return coordinates;
    }
    
    // 在光标位置插入@提及
    function insertMentionAtCursor(userId, userType, username) {
        const text = messageInput.value;
        const cursorPos = messageInput.selectionStart;
        
        // 查找光标前的最后一个@符号位置
        let atIndex = -1;
        for (let i = cursorPos - 1; i >= 0; i--) {
            if (text[i] === '@') {
                atIndex = i;
                break;
            } else if (text[i] === ' ' || text[i] === '\n') {
                break;
            }
        }
        
        if (atIndex !== -1) {
            // 构建新的文本，用带有标记的提及替换@查询
            const prefix = userType === 'agent' ? '@agent:' : '@';
            const beforeAt = text.substring(0, atIndex);
            const afterCursor = text.substring(cursorPos);
            const newText = beforeAt + prefix + username + ' ' + afterCursor;
            
            // 更新输入框的值
            messageInput.value = newText;
            
            // 设置光标位置到提及之后
            const newCursorPos = atIndex + prefix.length + username.length + 1;
            messageInput.setSelectionRange(newCursorPos, newCursorPos);
        }
        
        // 隐藏提及菜单
        mentionMenu.classList.remove('d-block');
        
        // 聚焦输入框
        messageInput.focus();
    }
    
    // 插入提及（点击成员列表时）
    function insertMention(user) {
        // 在当前光标位置插入提及
        const prefix = user.is_agent ? '@agent:' : '@';
        const mentionText = prefix + user.username + ' ';
        
        // 获取当前光标位置
        const cursorPos = messageInput.selectionStart;
        const text = messageInput.value;
        const newText = text.substring(0, cursorPos) + mentionText + text.substring(cursorPos);
        
        // 更新输入框的值
        messageInput.value = newText;
        
        // 设置光标位置到提及之后
        const newCursorPos = cursorPos + mentionText.length;
        messageInput.setSelectionRange(newCursorPos, newCursorPos);
        
        // 聚焦输入框
        messageInput.focus();
    }
    
    // 处理回复消息
    function replyToMessage(messageId) {
        const messageElement = document.getElementById(`message-${messageId}`);
        if (!messageElement) return;
        
        // 将回复ID添加到发送消息时的数据中
        messageInput.dataset.replyTo = messageId;
        
        // 在输入框上方显示回复预览
        const sender = messageElement.querySelector('.message-sender').textContent;
        const content = messageElement.querySelector('.message-content').textContent;
        
        // 创建或更新回复预览
        let replyPreview = document.querySelector('.reply-preview-input');
        if (!replyPreview) {
            replyPreview = document.createElement('div');
            replyPreview.className = 'reply-preview-input';
            messageForm.parentElement.insertBefore(replyPreview, messageForm);
        }
        
        replyPreview.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <div class="reply-info">回复 ${sender}</div>
                    <div class="reply-text">${content.substring(0, 50)}${content.length > 50 ? '...' : ''}</div>
                </div>
                <button type="button" class="btn-close btn-sm" id="cancelReplyBtn"></button>
            </div>
        `;
        
        // 添加取消回复按钮事件
        document.getElementById('cancelReplyBtn').addEventListener('click', function() {
            replyPreview.remove();
            delete messageInput.dataset.replyTo;
        });
        
        // 聚焦输入框
        messageInput.focus();
    }
    
    // 处理文件上传
    function handleFileUpload(file) {
        if (!file) return;
        
        // 最大文件大小（10MB）
        const maxSize = 10 * 1024 * 1024;
        
        if (file.size > maxSize) {
            showErrorMessage(`文件过大，最大允许上传 ${formatFileSize(maxSize)}`);
            return;
        }
        
        // 保存附件
        attachment = file;
        
        // 显示附件预览
        attachmentPreview.innerHTML = '';
        attachmentPreview.classList.remove('d-none');
        
        const previewElement = document.createElement('div');
        previewElement.className = 'd-flex align-items-center';
        
        // 根据文件类型显示不同的预览
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = function(e) {
                previewElement.innerHTML = `
                    <img src="${e.target.result}" class="img-thumbnail me-2" style="max-height: 100px; max-width: 100px;">
                    <div>
                        <div>${file.name}</div>
                        <small class="text-muted">${formatFileSize(file.size)}</small>
                    </div>
                    <button type="button" class="btn btn-sm btn-link text-danger ms-auto remove-attachment">
                        <i class="bi bi-x-lg"></i>
                    </button>
                `;
                
                // 发送图片
                sendImageFile(file);
            };
            reader.readAsDataURL(file);
        } else {
            // 显示文件图标
            const fileIcon = getFileIcon(file.type);
            
            previewElement.innerHTML = `
                <i class="bi ${fileIcon} fs-1 me-3"></i>
                <div>
                    <div>${file.name}</div>
                    <small class="text-muted">${formatFileSize(file.size)}</small>
                </div>
                <button type="button" class="btn btn-sm btn-link text-danger ms-auto remove-attachment">
                    <i class="bi bi-x-lg"></i>
                </button>
            `;
            
            // 发送文件
            sendFile(file);
        }
        
        // 添加移除附件的事件监听
        previewElement.querySelector('.remove-attachment').addEventListener('click', clearAttachment);
        
        attachmentPreview.appendChild(previewElement);
    }
    
    // 发送图片文件
    function sendImageFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('group_id', groupId);
        
        fetch('/api/messages/upload-image/', {
            method: 'POST',
            body: formData
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error('图片上传失败');
                }
                return response.json();
            })
            .then(data => {
                sendMessage(data.url, 'image');
            })
            .catch(error => {
                console.error('图片上传错误', error);
                showErrorMessage('图片上传失败，请重试');
            });
    }
    
    // 发送普通文件
    function sendFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('group_id', groupId);
        
        fetch('/api/messages/upload-file/', {
            method: 'POST',
            body: formData
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error('文件上传失败');
                }
                return response.json();
            })
            .then(data => {
                const fileInfo = {
                    name: file.name,
                    size: file.size,
                    mime_type: file.type,
                    url: data.url
                };
                sendMessage(JSON.stringify(fileInfo), 'file');
            })
            .catch(error => {
                console.error('文件上传错误', error);
                showErrorMessage('文件上传失败，请重试');
            });
    }
    
    // 清除附件
    function clearAttachment() {
        attachment = null;
        attachmentPreview.innerHTML = '';
        attachmentPreview.classList.add('d-none');
        attachmentInput.value = '';
    }
    
    // 滚动到最新消息
    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    // 根据文件类型返回图标类名
    function getFileIcon(mimeType) {
        if (mimeType.startsWith('image/')) {
            return 'bi-file-image';
        } else if (mimeType.startsWith('video/')) {
            return 'bi-file-play';
        } else if (mimeType.startsWith('audio/')) {
            return 'bi-file-music';
        } else if (mimeType.includes('pdf')) {
            return 'bi-file-pdf';
        } else if (mimeType.includes('word') || mimeType.includes('document')) {
            return 'bi-file-word';
        } else if (mimeType.includes('excel') || mimeType.includes('sheet')) {
            return 'bi-file-excel';
        } else if (mimeType.includes('powerpoint') || mimeType.includes('presentation')) {
            return 'bi-file-ppt';
        } else if (mimeType.includes('zip') || mimeType.includes('compressed')) {
            return 'bi-file-zip';
        } else if (mimeType.includes('text/')) {
            return 'bi-file-text';
        } else if (mimeType.includes('json') || mimeType.includes('xml') || mimeType.includes('html')) {
            return 'bi-file-code';
        } else {
            return 'bi-file-earmark';
        }
    }
    
    // 格式化文件大小
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // 处理提及
    function processMentions(html) {
        // 处理@用户名
        let processedHtml = html.replace(/@([a-zA-Z0-9_\u4e00-\u9fa5]+)/g, function(match, username) {
            // 查找匹配的用户
            const member = groupMembers.find(m => 
                m.user.username.toLowerCase() === username.toLowerCase()
            );
            
            if (member) {
                const userType = member.user.is_agent ? 'agent' : 'user';
                const badgeClass = member.user.is_agent ? 'bg-success' : 'bg-primary';
                
                return `<span class="mention ${userType}-mention" data-user-id="${member.user.id}" data-user-type="${userType}">
                    <span class="badge ${badgeClass} me-1">@</span>${username}
                </span>`;
            }
            
            return match; // 如果没有找到匹配的用户，保持原样
        });
        
        // 处理@agent:用户名（明确的代理提及）
        processedHtml = processedHtml.replace(/@agent:([a-zA-Z0-9_\u4e00-\u9fa5]+)/g, function(match, username) {
            // 查找匹配的代理
            const member = groupMembers.find(m => 
                m.user.is_agent && m.user.username.toLowerCase() === username.toLowerCase()
            );
            
            if (member) {
                return `<span class="mention agent-mention" data-user-id="${member.user.id}" data-user-type="agent">
                    <span class="badge bg-success me-1">@</span>${username}
                </span>`;
            }
            
            return match; // 如果没有找到匹配的代理，保持原样
        });
        
        return processedHtml;
    }
    
    // 页面初始化
    init();
}); 