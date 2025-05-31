# 非嵌入式用户管理系统

这是一个独立的用户管理系统，允许其他网站通过简单的集成来使用统一的用户认证服务。系统提供类似 OAuth 的认证流程，支持多语言，并具有完整的用户权限管理功能。

## 功能特点

### 1. 核心功能

- 用户认证和授权
- 多级权限管理（普通用户、VIP、管理员）
- API 令牌支持
- 权限申请和审核流程
- 多语言支持（中文、英文、日文、韩文、法文）
- 基于 Redis 的会话管理

### 2. 系统架构

- 后端：Flask + SQLite + Redis
- 前端：HTML + CSS
- 认证：Session + API Token
- 数据存储：
  - user.db：用户信息
  - apply.db：权限申请记录

## 快速开始

### 1. 系统要求

- Python 3.7+
- Redis 服务器
- SQLite3

### 2. 安装配置

```bash
# 1. 克隆仓库
git clone [repository_url]

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置Redis连接
# 编辑 common/Config.py 中的Redis配置：
app.config['SESSION_REDIS'] = redis.Redis(
    host='your_redis_host',
    port=your_redis_port,
    password='your_redis_password'
)

# 4. 初始化数据库
python -c "from common.UserInformation import initialize_system; initialize_system()"
```

## 集成指南

### 1. 认证流程

1. 重定向到登录页面：

```javascript
// 在你的网站中重定向到认证服务器
window.location.href =
  "http://your-auth-server/login?redirect_uri=" +
  encodeURIComponent(window.location.href);
```

2. 用户完成登录后，系统将重定向回你的网站，并携带认证令牌：

```javascript
// 在你的回调页面中验证令牌
async function verifyToken(token) {
  const response = await fetch("http://your-auth-server/api/verify_token", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ token: token }),
  });
  return await response.json();
}
```

### 2. API 接口

#### 2.1 用户认证

```http
POST /api/login
Content-Type: application/json

{
    "username": "user",
    "password": "password"
}
```

响应：

```json
{
  "success": true,
  "token": "api_token",
  "user": {
    "username": "user",
    "vip": false,
    "admin": false
  }
}
```

#### 2.2 验证令牌

```http
POST /api/verify_token
Content-Type: application/json

{
    "token": "api_token"
}
```

响应：

```json
{
  "valid": true,
  "user": {
    "username": "user",
    "vip": false,
    "admin": false
  }
}
```

### 3. 权限管理

系统支持三种权限级别：

- 普通用户：基本访问权限
- VIP 用户：额外功能访问权限
- 管理员：系统管理权限

用户可以通过权限申请系统申请升级权限：

```http
POST /api/apply_permission
Content-Type: application/json

{
    "permission": "vip",
    "reason": "申请理由"
}
```

## 安全说明

1. 密码安全

- 使用 Werkzeug 的 security 模块进行密码哈希
- 所有密码都经过加密存储
- 支持强制登出机制

2. 会话安全

- 基于 Redis 的会话管理
- 支持会话超时
- 防止会话固定攻击

3. API 安全

- 基于令牌的 API 认证
- 支持令牌过期和刷新
- 请求频率限制

## 自定义配置

### 1. 多语言支持

在`translations`目录下添加新的语言支持：

```bash
pybabel extract -F babel.cfg -o messages.pot .
pybabel init -i messages.pot -d translations -l [语言代码]
pybabel compile -d translations
```

### 2. 样式定制

可以通过修改`static/style.css`来自定义界面样式。

## 常见问题

1. Redis 连接失败

- 检查 Redis 服务器是否正常运行
- 验证连接配置是否正确
- 确认防火墙设置

2. 跨域问题

- 在配置中添加允许的域名
- 使用 CORS 中间件
- 确保请求包含正确的头部

## 开发计划

- [ ] 添加 OAuth 2.0 支持
- [ ] 实现手机号验证
- [ ] 添加第三方登录支持
- [ ] 优化 API 性能
- [ ] 增加更多的统计功能

## 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进项目。在提交代码前，请确保：

1. 代码符合 PEP 8 规范
2. 添加了必要的测试
3. 更新了相关文档

## 许可证

MIT License
