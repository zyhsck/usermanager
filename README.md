# 用户管理系统

这是一个基于 Flask 的用户管理系统，提供用户认证、数据管理、OAuth 授权等功能。

## API 接口

### 认证说明

系统支持两种认证方式：

1. 会话认证（默认）

   - 通过登录接口获取会话
   - 适用于浏览器环境

2. Server Token 认证
   - 使用 server_settings 中配置的 server_token
   - 具有管理员权限
   - 适用于服务器间通信

### 用户数据 API

#### GET /api/user_data

获取用户数据

**参数：**

- `key` (可选)：数据键名，指定时只返回该键的数据
- `username` (可选，需管理员权限)：目标用户名，指定时返回该用户的数据
- `server_token` (可选)：服务器令牌，提供后具有管理员权限

**示例请求：**

```
GET /api/user_data?key=profile
GET /api/user_data?username=testuser&server_token=your_server_token_here
```

**成功响应：**

```json
// 单个数据
{
  "id": 1,
  "user_id": "user123",
  "data_key": "profile",
  "data_value": {
    "name": "张三",
    "age": 30,
    "email": "zhangsan@example.com",
    "department": "技术部",
    "position": "高级工程师",
    "skills": ["Python", "JavaScript", "Docker"],
    "joinDate": "2023-01-15"
  },
  "created_at": "2023-01-01 12:00:00",
  "updated_at": "2023-01-02 13:00:00"
}

// 多个数据
[
  {
    "id": 1,
    "user_id": "user123",
    "data_key": "profile",
    "data_value": {
      "name": "张三",
      "age": 30,
      "department": "技术部"
    },
    "created_at": "2023-01-01 12:00:00",
    "updated_at": "2023-01-02 13:00:00"
  },
  {
    "id": 2,
    "user_id": "user123",
    "data_key": "settings",
    "data_value": {
      "theme": "dark",
      "notifications": {
        "email": true,
        "desktop": false,
        "mobile": true
      },
      "language": "zh-CN",
      "timezone": "Asia/Shanghai"
    },
    "created_at": "2023-01-01 12:30:00",
    "updated_at": "2023-01-02 14:00:00"
  }
]
```

#### POST /api/user_data

添加或更新用户数据

**请求体：**

```json
{
  "key": "profile",
  "value": {
    "name": "张三",
    "age": 30,
    "email": "zhangsan@example.com",
    "department": "技术部",
    "position": "高级工程师",
    "skills": ["Python", "JavaScript", "Docker"],
    "joinDate": "2023-01-15"
  },
  "username": "testuser", // 可选，需管理员权限
  "server_token": "your_server_token_here" // 可选，提供后具有管理员权限
}
```

**参数说明：**

- `key` (必需)：数据键名，最大 50 字符
- `value` (必需)：数据值，最大 1000 字符，可以是字符串、数字、对象或数组
- `username` (可选)：目标用户名，需要管理员权限
- `server_token` (可选)：服务器令牌，提供后具有管理员权限

**成功响应：**

```json
{
  "message": "数据操作成功",
  "data": {
    "id": 1,
    "user_id": "user123",
    "data_key": "profile",
    "data_value": {
      "name": "张三",
      "age": 30,
      "email": "zhangsan@example.com",
      "department": "技术部",
      "position": "高级工程师",
      "skills": ["Python", "JavaScript", "Docker"],
      "joinDate": "2023-01-15"
    },
    "created_at": "2023-01-01 12:00:00",
    "updated_at": "2023-01-02 13:00:00"
  }
}
```

#### DELETE /api/user_data

删除用户数据

**参数：**

- `key` (必需)：要删除的数据键名
- `username` (可选)：目标用户名，需要管理员权限
- `server_token` (可选)：服务器令牌，提供后具有管理员权限

**示例请求：**

```
DELETE /api/user_data?key=profile
DELETE /api/user_data?key=profile&username=testuser&server_token=your_server_token_here
```

**成功响应：**

```json
{
  "message": "数据删除成功",
  "data": null
}
```

### 批量数据操作 API

#### POST /api/user_data/bulk

批量添加/更新/获取数据

**请求体：**

```json
{
  "server_token": "your_server_token_here", // 可选，提供后具有管理员权限
  "operations": [
    {
      "key": "profile",
      "value": {
        "name": "张三",
        "age": 30,
        "email": "zhangsan@example.com",
        "department": "技术部",
        "position": "高级工程师"
      },
      "action": "add",
      "username": "testuser" // 可选，需管理员权限
    },
    {
      "key": "settings",
      "value": {
        "theme": "dark",
        "notifications": {
          "email": true,
          "desktop": false,
          "mobile": true
        },
        "language": "zh-CN",
        "timezone": "Asia/Shanghai"
      },
      "action": "update"
    },
    {
      "key": "preferences",
      "action": "get"
    }
  ]
}
```

**参数说明：**

- `server_token` (可选)：服务器令牌，提供后具有管理员权限
- `operations` (必需)：操作数组
  - `key` (必需)：数据键名，最大 50 字符
  - `value` (add/update 操作必需)：数据值，最大 1000 字符
  - `action` (必需)：操作类型，可选值：
    - `add`: 添加新数据
    - `update`: 更新已有数据
    - `get`: 获取数据
    - `delete`: 删除数据
  - `username` (可选)：目标用户名，需要管理员权限

**成功响应：**

```json
{
  "message": "批量操作完成，成功2条，失败1条",
  "success_count": 2,
  "total_count": 3,
  "results": [
    {
      "key": "profile",
      "status": "success",
      "data": {
        "id": 1,
        "user_id": "testuser",
        "data_key": "profile",
        "data_value": {
          "name": "张三",
          "age": 30,
          "email": "zhangsan@example.com",
          "department": "技术部",
          "position": "高级工程师"
        }
      }
    },
    {
      "key": "settings",
      "status": "success",
      "data": {
        "id": 2,
        "user_id": "user123",
        "data_key": "settings",
        "data_value": {
          "theme": "dark",
          "notifications": {
            "email": true,
            "desktop": false,
            "mobile": true
          },
          "language": "zh-CN",
          "timezone": "Asia/Shanghai"
        }
      }
    }
  ],
  "failed_operations": [
    {
      "key": "preferences",
      "error": "数据不存在"
    }
  ]
}
```

#### DELETE /api/user_data/bulk

批量删除数据

**请求体 (方式 1 - 推荐)：**

```json
{
  "server_token": "your_server_token_here", // 可选，提供后具有管理员权限
  "operations": [
    {
      "key": "temporary_data",
      "action": "delete",
      "username": "testuser" // 可选，需管理员权限
    },
    {
      "key": "old_settings",
      "action": "delete"
    }
  ]
}
```

**请求体 (方式 2 - 兼容旧格式)：**

```json
{
  "server_token": "your_server_token_here", // 可选，提供后具有管理员权限
  "keys": ["temporary_data", "old_settings", "cache"]
}
```

**成功响应：**

```json
{
  "message": "批量删除完成，成功2条，失败1条",
  "success_count": 2,
  "total_count": 3,
  "failed_operations": [
    {
      "key": "cache",
      "error": "数据不存在"
    }
  ]
}
```

### OAuth 相关 API

#### GET /api/oauth/clients

获取 OAuth 客户端列表

**参数：**

- `server_token` (可选)：服务器令牌，提供后具有管理员权限

**响应示例：**

```json
[
  {
    "client_id": "abc123",
    "name": "企业门户系统",
    "redirect_uri": "https://portal.example.com/oauth/callback",
    "created_at": "2023-01-01 12:00:00",
    "is_active": true,
    "scopes": ["read", "write"],
    "last_used": "2023-05-15 08:30:00"
  }
]
```

#### POST /api/oauth/clients

创建新的 OAuth 客户端

**请求体：**

```json
{
  "server_token": "your_server_token_here", // 可选，提供后具有管理员权限
  "name": "企业门户系统",
  "redirect_uri": "https://portal.example.com/oauth/callback",
  "is_active": true,
  "scopes": ["read", "write"]
}
```

**成功响应：**

```json
{
  "message": "OAuth客户端创建成功",
  "client": {
    "client_id": "abc123",
    "client_secret": "xyz789",
    "name": "企业门户系统",
    "redirect_uri": "https://portal.example.com/oauth/callback",
    "is_active": true,
    "scopes": ["read", "write"],
    "created_at": "2023-05-20 10:00:00"
  }
}
```

#### PUT /api/oauth/clients

更新 OAuth 客户端

**请求体：**

```json
{
  "server_token": "your_server_token_here", // 可选，提供后具有管理员权限
  "client_id": "abc123",
  "name": "更新后的系统名称",
  "redirect_uri": "https://new-portal.example.com/oauth/callback",
  "is_active": true,
  "scopes": ["read", "write", "admin"]
}
```

**成功响应：**

```json
{
  "message": "OAuth客户端更新成功",
  "client": {
    "client_id": "abc123",
    "name": "更新后的系统名称",
    "redirect_uri": "https://new-portal.example.com/oauth/callback",
    "is_active": true,
    "scopes": ["read", "write", "admin"],
    "updated_at": "2023-05-20 11:00:00"
  }
}
```

#### DELETE /api/oauth/clients

删除 OAuth 客户端

**参数：**

- `client_id` (必需)：要删除的客户端 ID
- `server_token` (可选)：服务器令牌，提供后具有管理员权限

**示例请求：**

```
DELETE /api/oauth/clients?client_id=abc123&server_token=your_server_token_here
```

**成功响应：**

```json
{
  "message": "OAuth客户端删除成功"
}
```

## 数据示例

### 用户配置文件 (profile)

```json
{
  "key": "profile",
  "value": {
    "name": "张三",
    "age": 30,
    "email": "zhangsan@example.com",
    "department": "技术部",
    "position": "高级工程师",
    "skills": ["Python", "JavaScript", "Docker"],
    "education": {
      "degree": "硕士",
      "major": "计算机科学",
      "school": "示例大学",
      "graduationYear": 2020
    },
    "contact": {
      "phone": "13800138000",
      "address": "北京市海淀区",
      "emergency": {
        "name": "李四",
        "relationship": "朋友",
        "phone": "13900139000"
      }
    },
    "joinDate": "2023-01-15",
    "projects": [
      {
        "name": "用户管理系统",
        "role": "技术负责人",
        "period": "2023-01 至今"
      }
    ]
  }
}
```

### 用户设置 (settings)

```json
{
  "key": "settings",
  "value": {
    "theme": "dark",
    "notifications": {
      "email": {
        "enabled": true,
        "frequency": "daily",
        "types": ["security", "updates"]
      },
      "desktop": {
        "enabled": false
      },
      "mobile": {
        "enabled": true,
        "quiet_hours": {
          "start": "22:00",
          "end": "08:00"
        }
      }
    },
    "language": "zh-CN",
    "timezone": "Asia/Shanghai",
    "accessibility": {
      "fontSize": "medium",
      "highContrast": false,
      "reduceMotion": true
    },
    "privacy": {
      "shareProfile": "contacts_only",
      "showOnline": true,
      "allowMessages": "all"
    },
    "security": {
      "twoFactorAuth": true,
      "sessionTimeout": 3600,
      "trustedDevices": ["laptop-home", "iphone-12"]
    }
  }
}
```

### 应用偏好设置 (preferences)

```json
{
  "key": "preferences",
  "value": {
    "dashboard": {
      "layout": "grid",
      "widgets": [
        {
          "id": "calendar",
          "position": 1,
          "visible": true
        },
        {
          "id": "tasks",
          "position": 2,
          "visible": true
        },
        {
          "id": "notifications",
          "position": 3,
          "visible": false
        }
      ]
    },
    "editor": {
      "font": "Source Code Pro",
      "fontSize": 14,
      "tabSize": 2,
      "autoSave": true,
      "wordWrap": "on"
    },
    "communication": {
      "emailDigest": "weekly",
      "chatStatus": "available",
      "autoReply": {
        "enabled": false,
        "message": "我现在不在，稍后回复"
      }
    }
  }
}
```
