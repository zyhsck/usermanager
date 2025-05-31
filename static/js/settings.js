// 个人信息相关函数
async function saveProfile() {
    const form = document.getElementById('profileForm');
    const formData = new FormData(form);
    
    try {
        const response = await fetch('/api/settings/profile', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (response.ok) {
            showMessage('success', data.message);
        } else {
            showMessage('error', data.error);
        }
    } catch (error) {
        showMessage('error', '保存个人信息失败：' + error.message);
    }
}

// 服务器配置相关函数
async function saveServerConfig() {
    const form = document.getElementById('serverConfigForm');
    const formData = new FormData(form);
    const config = {};
    
    // 处理基本配置
    config.server_name = formData.get('server_name');
    config.allow_registration = formData.get('allow_registration') === 'on';
    config.max_users = parseInt(formData.get('max_users'));
    config.session_timeout = parseInt(formData.get('session_timeout'));
    config.log_level = formData.get('log_level');
    config.maintenance_mode = formData.get('maintenance_mode') === 'on';
    config.maintenance_message = formData.get('maintenance_message');
    
    // 处理SMTP设置
    config.smtp_settings = {
        enabled: formData.get('smtp_settings.enabled') === 'on',
        server: formData.get('smtp_settings.server'),
        port: parseInt(formData.get('smtp_settings.port')),
        username: formData.get('smtp_settings.username'),
        password: formData.get('smtp_settings.password'),
        use_tls: formData.get('smtp_settings.use_tls') === 'on',
        from_email: formData.get('smtp_settings.from_email')
    };
    
    try {
        const response = await fetch('/api/settings/server', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        const data = await response.json();
        if (response.ok) {
            showMessage('success', data.message);
        } else {
            showMessage('error', data.error);
        }
    } catch (error) {
        showMessage('error', '保存服务器配置失败：' + error.message);
    }
}

// OAuth客户端管理相关函数
function showAddClientForm() {
    document.getElementById('formTitle').textContent = '添加新客户端';
    document.getElementById('clientId').value = '';
    document.getElementById('clientName').value = '';
    document.getElementById('redirectUri').value = '';
    document.getElementById('clientForm').style.display = 'block';
}

function hideClientForm() {
    document.getElementById('clientForm').style.display = 'none';
}

async function editClient(clientId) {
    try {
        const response = await fetch(`/api/oauth/clients?client_id=${clientId}`);
        const data = await response.json();
        
        if (response.ok) {
            document.getElementById('formTitle').textContent = '编辑客户端';
            document.getElementById('clientId').value = clientId;
            document.getElementById('clientName').value = data.name;
            document.getElementById('redirectUri').value = data.redirect_uri;
            document.getElementById('clientForm').style.display = 'block';
        } else {
            showMessage('error', data.error);
        }
    } catch (error) {
        showMessage('error', '获取客户端信息失败：' + error.message);
    }
}

async function deleteClient(clientId) {
    if (!confirm('确定要删除这个客户端吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/oauth/clients?client_id=${clientId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        if (response.ok) {
            showMessage('success', data.message);
            // 刷新客户端列表
            location.reload();
        } else {
            showMessage('error', data.error);
        }
    } catch (error) {
        showMessage('error', '删除客户端失败：' + error.message);
    }
}

async function handleClientSubmit(event) {
    event.preventDefault();
    
    const form = document.getElementById('oauthClientForm');
    const formData = new FormData(form);
    const clientId = formData.get('client_id');
    
    const data = {
        name: formData.get('name'),
        redirect_uri: formData.get('redirect_uri')
    };
    
    try {
        const response = await fetch('/api/oauth/clients', {
            method: clientId ? 'PUT' : 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(clientId ? { ...data, client_id: clientId } : data)
        });
        
        const responseData = await response.json();
        if (response.ok) {
            showMessage('success', responseData.message);
            if (responseData.client && !clientId) {
                // 显示新创建的客户端凭据
                showClientCredentials(responseData.client);
            } else {
                // 刷新页面以显示更新
                location.reload();
            }
        } else {
            showMessage('error', responseData.error);
        }
    } catch (error) {
        showMessage('error', '保存客户端失败：' + error.message);
    }
}

// 辅助函数
function showMessage(type, message) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.textContent = message;
    
    document.querySelector('.settings-container').insertBefore(
        messageDiv,
        document.querySelector('.settings-container').firstChild
    );
    
    setTimeout(() => messageDiv.remove(), 5000);
}

function showClientCredentials(client) {
    const html = `
        <div class="credentials-dialog">
            <h4>新客户端凭据</h4>
            <p class="warning">请立即保存这些信息，客户端密钥只会显示一次！</p>
            <div class="credentials">
                <div class="credential-item">
                    <label>客户端ID:</label>
                    <input type="text" readonly value="${client.client_id}">
                    <button onclick="copyToClipboard(this.previousElementSibling)">复制</button>
                </div>
                <div class="credential-item">
                    <label>客户端密钥:</label>
                    <input type="text" readonly value="${client.client_secret}">
                    <button onclick="copyToClipboard(this.previousElementSibling)">复制</button>
                </div>
            </div>
            <button onclick="this.parentElement.remove()">关闭</button>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', html);
}

function copyToClipboard(input) {
    input.select();
    document.execCommand('copy');
    showMessage('success', '已复制到剪贴板');
}