# API 请求示例文档

本文档提供了所有 API 端点的详细 JSON 请求示例。

## API 认证说明

### 认证方式

1. API Token 认证

   - 用于普通用户和管理员的 API 请求
   - 在请求体中添加 `api_token` 参数
   - 示例：`"api_token": "your-api-token-here"`
   - 所有需要用户认证的 API 调用都必须包含此参数

2. Server Token 认证
   - 用于服务器间通信和系统级操作
   - 在请求体中添加 `server_token` 参数
   - 示例：`"server_token": "your-server-token-here"`
   - 具有最高权限，可以执行所有操作

### 安全建议

1. 请妥善保管你的 API Token，不要泄露给他人
2. API Token 具有过期机制，需要定期更新
3. 建议使用 HTTPS 进行 API 调用，确保数据传输安全
4. 如果怀疑 Token 泄露，请立即更换

## 用户数据 API

### 1. 获取用户数据

#### 示例 1：获取当前用户所有数据

```json
// GET /api/user_data
{
  "username": "current_user",
  "api_token": "your-api-token-here"
}

// 响应
{
  "data": [
    {
      "id": 1,
      "user_id": "current_user",
      "data_key": "profile",
      "data_value": {
        "nickname": "测试用户",
        "avatar": "avatar.jpg"
      },
      "created_at": "2023-01-01 12:00:00",
      "updated_at": "2023-01-01 12:00:00"
    }
  ],
  "message": "获取成功"
}
```

#### 示例 2：获取指定用户的特定数据（管理员）

```json
// GET /api/user_data?key=profile&username=test_user
{
  "username": "admin",
  "api_token": "admin-api-token-here"
}

// 响应
{
  "data": {
    "id": 2,
    "user_id": "test_user",
    "data_key": "profile",
    "data_value": {
      "nickname": "测试用户",
      "avatar": "default.jpg"
    },
    "created_at": "2023-01-01 12:00:00",
    "updated_at": "2023-01-01 12:00:00"
  },
  "message": "获取成功"
}
```

#### 示例 3：使用 server_token 获取任意用户数据

```json
// GET /api/user_data?key=profile&username=test_user
{
  "server_token": "your-server-token-here"
}

// 响应
{
  "data": {
    "id": 2,
    "user_id": "test_user",
    "data_key": "profile",
    "data_value": {
      "nickname": "测试用户",
      "avatar": "default.jpg",
      "department": "技术部",
      "position": "工程师"
    },
    "created_at": "2023-01-01 12:00:00",
    "updated_at": "2023-01-01 12:00:00"
  },
  "message": "获取成功"
}
```

### 2. 添加/更新用户数据

#### 示例 1：更新当前用户数据

```json
// POST /api/user_data
{
  "key": "profile",
  "value": {
    "nickname": "新昵称",
    "avatar": "new_avatar.jpg"
  },
  "server_token":"test",
  "api_token": "your-api-token-here",
  "username": "current_user"
}
//server_token为个人在其他端post服务器时的管理员token(在server_config.json设置)
//username为当前用户需要在管理员或有server_token的前提下使用，否则只能在浏览器里登录后，不添加此参数使用（默认为用户名）
//api_token为当前用户token，不添加请求失败

// 响应
{
  "message": "数据更新成功",
  "data": {
    "id": 1,
    "user_id": "current_user",
    "data_key": "profile",
    "data_value": {
      "nickname": "新昵称",
      "avatar": "new_avatar.jpg"
    },
    "updated_at": "2023-01-01 12:00:00"
  }
}

//注意第一次生成会报错，但是会创建（可以忽视第一次报错）
```

#### 示例 2：管理员更新其他用户数据

```json
// POST /api/user_data
{
  "username": "test_user",
  "key": "settings",
  "value": {
    "theme": "dark",
    "notifications": true
  }
}

// 响应
{
  "message": "数据更新成功",
  "data": {
    "id": 2,
    "user_id": "test_user",
    "data_key": "settings",
    "data_value": {
      "theme": "dark",
      "notifications": true
    },
    "updated_at": "2023-01-01 12:00:00"
  }
}
```

#### 示例 3：使用 server_token 更新任意用户数据

```json
// POST /api/user_data
{
  "server_token": "your-server-token-here",
  "username": "test_user",
  "key": "profile",
  "value": {
    "nickname": "系统更新的昵称",
    "avatar": "system_avatar.jpg",
    "department": "研发部",
    "position": "高级工程师",
    "skills": ["Python", "JavaScript", "Docker"]
  }
}

// 响应
{
  "message": "数据更新成功",
  "data": {
    "id": 2,
    "user_id": "test_user",
    "data_key": "profile",
    "data_value": {
      "nickname": "系统更新的昵称",
      "avatar": "system_avatar.jpg",
      "department": "研发部",
      "position": "高级工程师",
      "skills": ["Python", "JavaScript", "Docker"]
    },
    "updated_at": "2023-01-01 12:00:00"
  }
}
```

### 3. 批量操作用户数据

#### 示例 1：批量添加和更新

```json
// POST /api/user_data/bulk
{
  "api_token": "your-api-token-here",
  "operations": [
    {
      "key": "profile",
      "value": {
        "nickname": "用户1",
        "avatar": "avatar1.jpg"
      },
      "action": "add"
    },
    {
      "key": "settings",
      "value": {
        "theme": "light",
        "language": "zh"
      },
      "action": "update"
    }
  ]
}

// 响应
{
  "message": "批量操作完成",
  "success_count": 2,
  "total_count": 2,
  "results": [
    {
      "key": "profile",
      "status": "success",
      "data": {
        "id": 1,
        "data_key": "profile",
        "data_value": {
          "nickname": "用户1",
          "avatar": "avatar1.jpg"
        }
      }
    },
    {
      "key": "settings",
      "status": "success",
      "data": {
        "id": 2,
        "data_key": "settings",
        "data_value": {
          "theme": "light",
          "language": "zh"
        }
      }
    }
  ]
}
```

#### 示例 2：批量删除

```json
// DELETE /api/user_data/bulk
{
  "api_token": "your-api-token-here",
  "operations": [
    {
      "key": "temporary_data",
      "action": "delete"
    },
    {
      "key": "cache",
      "action": "delete"
    }
  ]
}

// 响应
{
  "message": "批量删除完成",
  "success_count": 2,
  "total_count": 2,
  "deleted_keys": ["temporary_data", "cache"]
}
```

#### 示例 3：使用 server_token 批量操作多个用户数据

```json
// POST /api/user_data/bulk
{
  "server_token": "your-server-token-here",
  "operations": [
    {
      "key": "profile",
      "value": {
        "nickname": "系统用户1",
        "department": "市场部",
        "position": "经理"
      },
      "action": "update",
      "username": "user1"
    },
    {
      "key": "settings",
      "value": {
        "theme": "dark",
        "language": "zh-CN",
        "notifications": {
          "email": true,
          "desktop": false
        }
      },
      "action": "update",
      "username": "user2"
    },
    {
      "key": "temporary_data",
      "action": "delete",
      "username": "user3"
    }
  ]
}

// 响应
{
  "message": "批量操作完成",
  "success_count": 3,
  "total_count": 3,
  "results": [
    {
      "key": "profile",
      "username": "user1",
      "status": "success",
      "data": {
        "id": 5,
        "data_key": "profile",
        "data_value": {
          "nickname": "系统用户1",
          "department": "市场部",
          "position": "经理"
        }
      }
    },
    {
      "key": "settings",
      "username": "user2",
      "status": "success",
      "data": {
        "id": 8,
        "data_key": "settings",
        "data_value": {
          "theme": "dark",
          "language": "zh-CN",
          "notifications": {
            "email": true,
            "desktop": false
          }
        }
      }
    },
    {
      "key": "temporary_data",
      "username": "user3",
      "status": "success",
      "action": "delete"
    }
  ]
}
```

## 用户设置 API

### 1. 更新个人资料

#### 示例 1：基本信息更新

```json
// POST /api/settings/profile
{
  "api_token": "your-api-token-here",
  "display_name": "张三",
  "email": "zhangsan@example.com",
  "bio": "这是我的个人简介",
  "preferences": {
    "language": "zh",
    "timezone": "Asia/Shanghai",
    "notifications": {
      "email": true,
      "push": false
    }
  }
}

// 响应
{
  "message": "个人资料更新成功",
  "data": {
    "display_name": "张三",
    "email": "zhangsan@example.com",
    "bio": "这是我的个人简介",
    "preferences": {
      "language": "zh",
      "timezone": "Asia/Shanghai",
      "notifications": {
        "email": true,
        "push": false
      }
    },
    "updated_at": "2023-01-01 12:00:00"
  }
}
```

### 2. 更新服务器配置（管理员）

#### 示例 1：完整配置更新

```json
// POST /api/settings/server
{
  "app_settings": {
    "site_name": "用户管理系统",
    "debug": false,
    "maintenance_mode": false,
    "allowed_domains": ["example.com", "test.com"],
    "session_lifetime": 86400
  },
  "security_settings": {
    "password_policy": {
      "min_length": 8,
      "require_numbers": true,
      "require_special_chars": true
    },
    "login_attempts": {
      "max_attempts": 5,
      "lockout_duration": 300
    },
    "two_factor_auth": {
      "enabled": true,
      "methods": ["email", "authenticator"]
    }
  },
  "email_settings": {
    "smtp_server": "smtp.example.com",
    "smtp_port": 587,
    "smtp_username": "noreply@example.com",
    "smtp_password": "smtp_password",
    "from_email": "noreply@example.com",
    "from_name": "用户管理系统"
  },
  "server_settings": {
    "server_token": "your-secure-server-token-here",
    "api_rate_limit": 1000,
    "max_upload_size": 10485760
  }
}

// 响应
{
  "message": "服务器配置更新成功",
  "updated_sections": [
    "app_settings",
    "security_settings",
    "email_settings",
    "server_settings"
  ]
}
```

#### 示例 2：使用 server_token 更新配置

```json
// POST /api/settings/server
{
  "server_token": "your-server-token-here",
  "app_settings": {
    "site_name": "用户管理系统 - 企业版",
    "maintenance_mode": true,
    "maintenance_message": "系统正在升级，预计1小时后恢复"
  }
}

// 响应
{
  "message": "服务器配置更新成功",
  "updated_sections": [
    "app_settings"
  ]
}
```

## OAuth 客户端管理

### 1. 创建 OAuth 客户端

#### 示例 1：创建新客户端

```json
// POST /api/oauth/clients
{
  "api_token": "your-api-token-here",
  "name": "测试应用",
  "description": "这是一个测试应用",
  "redirect_uris": [
    "https://app.example.com/callback",
    "https://app.example.com/callback2"
  ],
  "allowed_grant_types": ["authorization_code", "refresh_token"],
  "scopes": ["read", "write", "profile"],
  "logo_url": "https://example.com/logo.png"
}

// 响应
{
  "message": "OAuth客户端创建成功",
  "client": {
    "client_id": "generated_client_id",
    "client_secret": "generated_client_secret",
    "name": "测试应用",
    "redirect_uris": [
      "https://app.example.com/callback",
      "https://app.example.com/callback2"
    ],
    "created_at": "2023-01-01 12:00:00"
  }
}
```

#### 示例 2：使用 server_token 创建 OAuth 客户端

```json
// POST /api/oauth/clients
{
  "server_token": "your-server-token-here",
  "name": "企业门户系统",
  "description": "公司内部门户系统",
  "redirect_uris": [
    "https://portal.company.com/oauth/callback"
  ],
  "allowed_grant_types": ["authorization_code", "client_credentials"],
  "scopes": ["read", "write", "admin"],
  "logo_url": "https://company.com/logo.png",
  "is_trusted": true
}

// 响应
{
  "message": "OAuth客户端创建成功",
  "client": {
    "client_id": "generated_client_id",
    "client_secret": "generated_client_secret",
    "name": "企业门户系统",
    "redirect_uris": [
      "https://portal.company.com/oauth/callback"
    ],
    "is_trusted": true,
    "created_at": "2023-01-01 12:00:00"
  }
}
```

### 2. 更新 OAuth 客户端

#### 示例 1：更新客户端信息

```json
// PUT /api/oauth/clients
{
  "api_token": "your-api-token-here",
  "client_id": "existing_client_id",
  "name": "更新后的应用名称",
  "description": "更新后的描述",
  "redirect_uris": [
    "https://new.example.com/callback"
  ],
  "is_active": true,
  "allowed_grant_types": ["authorization_code"],
  "scopes": ["read", "profile"]
}

// 响应
{
  "message": "OAuth客户端更新成功",
  "client": {
    "client_id": "existing_client_id",
    "name": "更新后的应用名称",
    "redirect_uris": [
      "https://new.example.com/callback"
    ],
    "updated_at": "2023-01-01 12:00:00"
  }
}
```

#### 示例 2：使用 server_token 更新 OAuth 客户端

```json
// PUT /api/oauth/clients
{
  "server_token": "your-server-token-here",
  "client_id": "existing_client_id",
  "name": "企业应用 - 新版",
  "is_active": true,
  "scopes": ["read", "write", "admin", "system"],
  "is_trusted": true,
  "rate_limit": 5000
}

// 响应
{
  "message": "OAuth客户端更新成功",
  "client": {
    "client_id": "existing_client_id",
    "name": "企业应用 - 新版",
    "is_active": true,
    "is_trusted": true,
    "scopes": ["read", "write", "admin", "system"],
    "rate_limit": 5000,
    "updated_at": "2023-01-01 12:00:00"
  }
}
```

## 通用 API 接口

### 1. 获取用户信息

#### 示例 1：获取基本信息

```json
// POST /api/get_user_info
{
  "username": "test_user",
  "api_token": "your-api-token-here"
}

// 响应
{
  "username": "test_user",
  "profile": {
    "display_name": "测试用户",
    "email": "test@example.com",
    "avatar_url": "https://example.com/avatars/test.jpg",
    "bio": "用户简介"
  },
  "stats": {
    "register_time": "2023-01-01 12:00:00",
    "last_login": "2023-01-02 12:00:00",
    "login_count": 10
  },
  "roles": ["user"],
  "permissions": ["read", "write"]
}
```

#### 示例 2：使用 server_token 获取详细用户信息

```json
// POST /api/get_user_info
{
  "server_token": "your-server-token-here",
  "username": "test_user",
  "include_sensitive": true
}

// 响应
{
  "username": "test_user",
  "profile": {
    "display_name": "测试用户",
    "email": "test@example.com",
    "phone": "13800138000",
    "avatar_url": "https://example.com/avatars/test.jpg",
    "bio": "用户简介"
  },
  "stats": {
    "register_time": "2023-01-01 12:00:00",
    "last_login": "2023-01-02 12:00:00",
    "login_count": 10,
    "failed_login_attempts": 2,
    "last_failed_login": "2023-01-01 10:00:00",
    "last_ip": "192.168.1.100"
  },
  "roles": ["user"],
  "permissions": ["read", "write"],
  "account_status": "active",
  "security": {
    "two_factor_enabled": true,
    "password_last_changed": "2023-01-01 09:00:00",
    "recovery_email": "backup@example.com"
  },
  "custom_fields": {
    "department": "技术部",
    "employee_id": "EMP001",
    "hire_date": "2022-01-01"
  }
}
```

### 2. 获取服务器信息

#### 示例 1：获取完整信息

```json
// POST /api/get_server_info
{
  "username": "admin",
  "api_token": "admin-api-token-here",
  "include_stats": true
}

// 响应
{
  "version": "1.0.0",
  "status": {
    "uptime": "10 days",
    "current_time": "2023-01-01 12:00:00",
    "timezone": "UTC"
  },
  "stats": {
    "total_users": 1000,
    "active_users": 500,
    "total_requests": 10000,
    "cpu_usage": 45.5,
    "memory_usage": 60.2
  },
  "system": {
    "os": "Linux",
    "python_version": "3.9.0",
    "database": "PostgreSQL 13.4"
  }
}
```

#### 示例 2：使用 server_token 获取详细服务器信息

```json
// POST /api/get_server_info
{
  "server_token": "your-server-token-here",
  "include_stats": true,
  "include_config": true
}

// 响应
{
  "version": "1.0.0",
  "status": {
    "uptime": "10 days",
    "current_time": "2023-01-01 12:00:00",
    "timezone": "UTC",
    "maintenance_mode": false
  },
  "stats": {
    "total_users": 1000,
    "active_users": 500,
    "total_requests": 10000,
    "requests_per_minute": 16.7,
    "cpu_usage": 45.5,
    "memory_usage": 60.2,
    "disk_usage": 35.8,
    "database_size": "1.2 GB"
  },
  "system": {
    "os": "Linux",
    "python_version": "3.9.0",
    "database": "PostgreSQL 13.4",
    "web_server": "Nginx 1.18.0",
    "host": "server-prod-01"
  },
  "config": {
    "app_settings": {
      "site_name": "用户管理系统",
      "debug": false,
      "allowed_domains": ["example.com", "test.com"]
    },
    "security_settings": {
      "password_policy": {
        "min_length": 8,
        "require_numbers": true
      },
      "two_factor_auth": {
        "enabled": true
      }
    },
    "server_settings": {
      "api_rate_limit": 1000,
      "max_upload_size": 10485760
    }
  }
}
```

### 3. 删除用户（管理员）

#### 示例 1：删除单个用户

```json
// POST /api/delete_user
{
  "username": "admin",
  "api_token": "admin-api-token-here",
  "target_user": "user_to_delete",
  "reason": "账户违规",
  "backup_data": true
}

// 响应
{
  "message": "用户删除成功",
  "details": {
    "deleted_user": "user_to_delete",
    "deleted_at": "2023-01-01 12:00:00",
    "backup_file": "backups/user_to_delete_20230101120000.zip"
  }
}
```

#### 示例 2：使用 server_token 删除用户

```json
// POST /api/delete_user
{
  "server_token": "your-server-token-here",
  "target_user": "user_to_delete",
  "reason": "系统自动清理",
  "backup_data": true,
  "notify_user": true,
  "permanent": false
}

// 响应
{
  "message": "用户删除成功",
  "details": {
    "deleted_user": "user_to_delete",
    "deleted_at": "2023-01-01 12:00:00",
    "backup_file": "backups/user_to_delete_20230101120000.zip",
    "notification_sent": true,
    "deletion_type": "soft_delete"
  }
}
```

## 数据示例

### 用户配置文件 (profile)

```json
{
  "key": "profile",
  "value": {
    "nickname": "张三",
    "avatar": "avatar.jpg",
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
