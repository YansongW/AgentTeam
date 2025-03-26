/**
 * WebSocket消息管理模块
 */
class MessageWebSocket {
    constructor(options = {}) {
        this.socket = null;
        this.connected = false;
        this.messageIds = [];
        this.userId = options.userId || `user_${Math.floor(Math.random() * 10000)}`;
        this.username = options.username || 'Guest';
        this.sessionId = null;
        this.room = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = options.maxReconnectAttempts || 5;
        this.reconnectInterval = options.reconnectInterval || 3000;
        this.autoReconnect = options.autoReconnect !== false;
        this.listeners = {
            message: [],
            connect: [],
            disconnect: [],
            error: [],
            typing: [],
            readReceipt: []
        };
    }

    /**
     * 连接到WebSocket服务器
     * @param {string} room - 房间ID
     * @returns {Promise} 连接结果
     */
    connect(room) {
        return new Promise((resolve, reject) => {
            if (this.socket) {
                this.socket.close();
            }

            this.room = room;
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/messaging/${room}/`;
            
            this.socket = new WebSocket(wsUrl);
            
            this.socket.onopen = (e) => {
                this.connected = true;
                this.reconnectAttempts = 0;
                this._trigger('connect', { event: e });
                resolve(e);
            };
            
            this.socket.onmessage = (e) => {
                const data = JSON.parse(e.data);
                this._handleIncomingMessage(data);
            };
            
            this.socket.onclose = (e) => {
                this.connected = false;
                this._trigger('disconnect', { event: e, reason: 'WebSocket连接已关闭' });
                
                if (this.autoReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
                    setTimeout(() => {
                        this.reconnectAttempts++;
                        this.connect(this.room);
                    }, this.reconnectInterval);
                }
                
                reject(e);
            };
            
            this.socket.onerror = (e) => {
                this._trigger('error', { event: e, message: 'WebSocket连接发生错误' });
                reject(e);
            };
        });
    }

    /**
     * 断开WebSocket连接
     */
    disconnect() {
        if (this.socket) {
            this.autoReconnect = false;
            this.socket.close();
            this.socket = null;
        }
    }

    /**
     * 发送消息
     * @param {string} text - 消息文本
     * @param {object} options - 额外选项
     * @returns {string} 消息ID
     */
    sendMessage(text, options = {}) {
        if (!this.connected || !this.socket) {
            this._trigger('error', { message: '未连接到服务器' });
            return null;
        }
        
        const messageId = this._generateId();
        const message = {
            message_id: messageId,
            message_type: options.messageType || "chat",
            sender: {
                id: this.userId,
                type: "user",
                name: this.username
            },
            timestamp: new Date().toISOString(),
            payload: {
                text: text,
                format: options.format || "text"
            },
            metadata: {
                client_info: {
                    platform: "web",
                    device: "browser"
                },
                ...options.metadata
            }
        };
        
        this.socket.send(JSON.stringify(message));
        this.messageIds.push(messageId);
        return messageId;
    }

    /**
     * 发送正在输入状态
     * @param {number} remainingTextLength - 当前输入框中的字符数量
     */
    sendTypingStatus(remainingTextLength = 0) {
        if (!this.connected || !this.socket) return;
        
        const message = {
            message_id: this._generateId(),
            message_type: "typing",
            sender: {
                id: this.userId,
                type: "user",
                name: this.username
            },
            timestamp: new Date().toISOString(),
            payload: {
                status: "typing",
                remaining_text: remainingTextLength
            },
            metadata: {}
        };
        
        this.socket.send(JSON.stringify(message));
    }

    /**
     * 发送已读回执
     * @param {Array|string} messageIds - 已读消息ID列表或单个消息ID
     */
    sendReadReceipt(messageIds) {
        if (!this.connected || !this.socket) return;
        
        const ids = Array.isArray(messageIds) ? messageIds : [messageIds];
        
        const message = {
            message_id: this._generateId(),
            message_type: "read_receipt",
            sender: {
                id: this.userId,
                type: "user",
                name: this.username
            },
            timestamp: new Date().toISOString(),
            payload: {
                message_ids: ids
            },
            metadata: {}
        };
        
        this.socket.send(JSON.stringify(message));
    }

    /**
     * 发送Ping消息
     */
    sendPing() {
        if (!this.connected || !this.socket) return;
        
        const message = {
            message_id: this._generateId(),
            message_type: "ping",
            sender: {
                id: this.userId,
                type: "user",
                name: this.username
            },
            timestamp: new Date().toISOString(),
            payload: {},
            metadata: {}
        };
        
        this.socket.send(JSON.stringify(message));
    }

    /**
     * 添加事件监听器
     * @param {string} event - 事件名称
     * @param {Function} callback - 回调函数
     */
    on(event, callback) {
        if (this.listeners[event]) {
            this.listeners[event].push(callback);
        }
        return this;
    }

    /**
     * 移除事件监听器
     * @param {string} event - 事件名称
     * @param {Function} callback - 回调函数
     */
    off(event, callback) {
        if (this.listeners[event]) {
            this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
        }
        return this;
    }

    /**
     * 处理收到的消息
     * @private
     * @param {object} data - 消息数据
     */
    _handleIncomingMessage(data) {
        console.log("收到消息:", data);
        
        switch (data.message_type) {
            case "connect_ack":
                this.sessionId = data.payload.session_id;
                break;
                
            case "chat":
            case "agent_response":
                this._trigger('message', { data });
                break;
                
            case "typing":
                this._trigger('typing', { data });
                break;
                
            case "read_receipt":
                this._trigger('readReceipt', { data });
                break;
                
            case "error":
                this._trigger('error', { message: data.payload.text, data });
                break;
                
            case "pong":
                // 处理pong响应
                break;
                
            default:
                console.log(`未处理的消息类型: ${data.message_type}`);
        }
    }

    /**
     * 触发事件
     * @private
     * @param {string} event - 事件名称
     * @param {object} data - 事件数据
     */
    _trigger(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`事件${event}回调执行错误:`, error);
                }
            });
        }
    }

    /**
     * 生成唯一ID
     * @private
     * @returns {string} 唯一ID
     */
    _generateId() {
        return 'msg_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    }
}

// 导出模块
window.MessageWebSocket = MessageWebSocket; 