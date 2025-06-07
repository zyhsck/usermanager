document.addEventListener('DOMContentLoaded', function() {
    // 当前是否处于编辑模式
    let isEditing = false;
    let currentKey = '';

    // 添加数据按钮点击事件
    document.getElementById('addDataBtn').addEventListener('click', function() {
        isEditing = false;
        resetDataForm();
        document.getElementById('dataModalLabel').innerHTML = '<i class="fas fa-plus me-2"></i>添加数据';
        document.getElementById('submitData').innerHTML = '<i class="fas fa-save me-1"></i>添加';
        new bootstrap.Modal(document.getElementById('dataModal')).show();
    });

    // 编辑按钮点击事件
    document.querySelectorAll('.edit-btn').forEach(button => {
        button.addEventListener('click', function() {
            isEditing = true;
            currentKey = this.getAttribute('data-key');
            const value = this.getAttribute('data-value');
            const username = this.getAttribute('data-user');

            document.getElementById('dataKey').value = currentKey;
            document.getElementById('dataValue').value = value;
            if (username) {
                document.getElementById('username').value = username;
            }

            document.getElementById('dataKey').readOnly = true;
            document.getElementById('dataModalLabel').innerHTML = '<i class="fas fa-edit me-2"></i>编辑数据';
            document.getElementById('submitData').innerHTML = '<i class="fas fa-save me-1"></i>更新';

            new bootstrap.Modal(document.getElementById('dataModal')).show();
        });
    });

    // 删除按钮点击事件
    document.querySelectorAll('.delete-btn').forEach(button => {
        button.addEventListener('click', function() {
            currentKey = this.getAttribute('data-key');
            const username = this.getAttribute('data-user');
            // 如果按钮上有data-user属性，保存到隐藏字段中
            if (username) {
                document.getElementById('deleteUsername').value = username;
            } else {
                document.getElementById('deleteUsername').value = '';
            }
            new bootstrap.Modal(document.getElementById('confirmDeleteModal')).show();
        });
    });

    // 确认删除按钮点击事件
    document.getElementById('confirmDeleteBtn').addEventListener('click', function() {
        const username = document.getElementById('deleteUsername').value;
        let url = `/api/user_data?key=${encodeURIComponent(currentKey)}`;
        if (username) {
            url += `&username=${encodeURIComponent(username)}`;
        }
        fetch(url, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                location.reload();
            } else if (data.error) {
                alert('删除失败：' + data.error);
            } else {
                alert('删除失败：未知错误');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('删除失败，请检查网络连接');
        });
    });

    // 提交数据（添加/更新）
    document.getElementById('submitData').addEventListener('click', function() {
        const username = document.getElementById('username').value;
        const dataKey = document.getElementById('dataKey').value;
        const dataValue = document.getElementById('dataValue').value;

        if (!dataKey || !dataValue) {
            alert('请填写所有必填字段');
            return;
        }

        const data = {
            key: dataKey,
            value: dataValue
        };

        // 如果用户名不为空且不是当前用户名，添加到请求数据中
        if (username && username !== document.getElementById('username').defaultValue) {
            data.username = username;
        }

        fetch('/api/user_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                location.reload();
            } else if (data.error) {
                alert((isEditing ? '更新失败：' : '添加失败：') + data.error);
            } else {
                alert(isEditing ? '更新失败：未知错误' : '添加失败：未知错误');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert(isEditing ? '更新失败，请检查网络连接' : '添加失败，请检查网络连接');
        });
    });

    // 重置表单数据
    function resetDataForm() {
        const usernameInput = document.getElementById('username');
        // 如果用户不是管理员（readonly属性存在），则重置为默认值
        if (usernameInput.readOnly) {
            usernameInput.value = usernameInput.defaultValue;
        }
        document.getElementById('dataKey').value = '';
        document.getElementById('dataKey').readOnly = false;
        document.getElementById('dataValue').value = '';
    }
});