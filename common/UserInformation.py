from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from uuid import uuid4
import secrets
import logging
from flask import session
from flask import current_app
from .db_setup import db

# 用户模型
class User(db.Model):
    __bind_key__ = 'user_db'
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    vip = db.Column(db.Boolean, default=False)
    admin = db.Column(db.Boolean, default=False)
    api_token = db.Column(db.String(200), unique=True, nullable=True)
    force_logout = db.Column(db.Boolean, default=False)
    register_time = db.Column(db.DateTime, default=db.func.current_timestamp())
    usericon_url = db.Column(db.String(200), nullable=True)
    # 新增个人信息字段
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    real_name = db.Column(db.String(50), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(100), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)


# 用户操作类
class UserInformation:

    @staticmethod
    def store_user(username, password, is_vip=False, is_admin=False, usericon_url=None):
        if User.query.filter_by(username=username).first():
            return False, "用户已存在"

        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username,
            password_hash=hashed_password,
            vip=is_vip,
            admin=is_admin,
            api_token=None,
            register_time=datetime.now().replace(microsecond=0),
            usericon_url=usericon_url)

        db.session.add(new_user)
        db.session.commit()
        return True, "用户注册成功!"

    @staticmethod
    def verify_user(username, password):
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            return {
                "username": user.username,
                "vip": user.vip,
                "admin": user.admin
            }
        return None
    
    @staticmethod
    def refresh_user_session(username):
        """
        建议不要直接操作 Redis 里的 session 数据。
        这里示例为通过 Flask 的 session 机制刷新用户权限，
        你需要在用户登录态或请求处理时调用该方法来同步权限。
        """
        try:
            user = User.query.filter_by(username=username).first()
            if not user:
                return False, "用户不存在"
            
            # 注意：这里假设你在请求上下文中调用该函数，否则 session 不可用
            session['vip'] = user.vip
            session['admin'] = user.admin
            # 也可更新其他权限信息

            # Flask 会自动保存 session，无需手动写入 Redis
            return True, "用户 session 已刷新"
        except RuntimeError:
            # 没有请求上下文，session 无法操作
            logging.error("刷新 session 时无请求上下文")
            return False, "刷新 session 失败：无请求上下文"

    @staticmethod
    def verify_api_token(username, token):
        user = User.query.filter_by(username=username).first()
        if user and user.api_token == token:
            return True
        return False

    @staticmethod
    def get_user_info(username):
        user = User.query.filter_by(username=username).first()
        if user:
            return {
                "username": user.username,
                "vip": user.vip,
                "admin": user.admin,
                "register_time": user.register_time.strftime('%Y-%m-%d %H:%M:%S'),
                "email": user.email,
                "phone": user.phone,
                "real_name": user.real_name,
                "bio": user.bio,
                "location": user.location,
                "website": user.website,
                "usericon_url": user.usericon_url,
                "last_login": user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None
            }
        return None

    @staticmethod
    def update_user_profile(username, profile_data):
        """更新用户个人信息"""
        user = User.query.filter_by(username=username).first()
        if not user:
            return False, "用户不存在"
            
        # 可更新的字段列表
        updateable_fields = [
            'email', 'phone', 'real_name', 'bio',
            'location', 'website', 'usericon_url'
        ]
        
        try:
            for field in updateable_fields:
                if field in profile_data:
                    setattr(user, field, profile_data[field])
            
            db.session.commit()
            return True, "个人信息更新成功"
        except Exception as e:
            db.session.rollback()
            return False, f"更新失败：{str(e)}"

    @staticmethod
    def manage_oauth_client(action, **kwargs):
        """管理OAuth客户端"""
        try:
            if action == 'create':
                client = OAuthClient(
                    name=kwargs['name'],
                    redirect_uri=kwargs['redirect_uri'],
                    created_by=kwargs['created_by'],
                    client_id=secrets.token_urlsafe(32),
                    client_secret=secrets.token_urlsafe(64)
                )
                if 'is_active' in kwargs:
                    client.is_active = kwargs['is_active']
                db.session.add(client)
                db.session.commit()
                return True, "OAuth客户端创建成功", client
                
            elif action == 'update':
                client = OAuthClient.query.filter_by(client_id=kwargs['client_id']).first()
                if not client:
                    return False, "OAuth客户端不存在", None
                    
                client.name = kwargs['name']
                client.redirect_uri = kwargs['redirect_uri']
                
                # 处理 is_active 字段
                if 'is_active' in kwargs:
                    client.is_active = kwargs['is_active']
                    
                db.session.commit()
                return True, "OAuth客户端更新成功", client
                
            elif action == 'delete':
                client = OAuthClient.query.filter_by(client_id=kwargs['client_id']).first()
                if not client:
                    return False, "OAuth客户端不存在", None
                    
                db.session.delete(client)
                db.session.commit()
                return True, "OAuth客户端删除成功", None
                
            elif action == 'list':
                clients = OAuthClient.query
                if 'created_by' in kwargs:
                    clients = clients.filter_by(created_by=kwargs['created_by'])
                return True, "获取成功", clients.all()
                
        except Exception as e:
            db.session.rollback()
            return False, f"操作失败：{str(e)}", None

    @staticmethod
    def get_users_name_list():
        users = User.query.all()
        user_list = []
        for user in users:
            user_list.append(user.username)
        return user_list

    @staticmethod
    def get_users_info_list():
        users = User.query.all()
        user_list = []
        for user in users:
            user_list.append({
                "username": user.username,
                "vip": user.vip,
                "admin": user.admin,
                "register_time": user.register_time.strftime('%Y-%m-%d %H:%M:%S'),
            })
        return user_list

    @staticmethod
    def delete_user(username):
        user = User.query.filter_by(username=username).first()
        if user:
            db.session.delete(user)
            db.session.commit()
            return True, "用户删除成功"
        return False, "用户不存在"

    @staticmethod
    def get_server_info():
        server_info = { 
            "users_num": User.query.count(),
            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "smtp_settings": {
                "host": current_app.config.get('MAIL_SERVER'),
                "port": current_app.config.get('MAIL_PORT'),
                "username": current_app.config.get('MAIL_USERNAME'),
                "password": "********",  # 出于安全考虑，不返回实际密码
                "use_tls": current_app.config.get('MAIL_USE_TLS', False),
                "from_email": current_app.config.get('MAIL_DEFAULT_SENDER')
            }
        }
        return server_info


# OAuth客户端模型
class OAuthClient(db.Model):
    __bind_key__ = 'oauth_db'
    __tablename__ = 'oauth_clients'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(100), unique=True, nullable=False)
    client_secret = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    redirect_uri = db.Column(db.String(500), nullable=False)
    created_by = db.Column(db.String(150), nullable=False)  # 关联到用户名
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    is_active = db.Column(db.Boolean, default=True, nullable=False)  # 控制客户端是否启用


# 权限申请模型
class UserApply(db.Model):
    __bind_key__ = 'apply_db'
    __tablename__ = 'user_apply'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    permission = db.Column(db.String(50), nullable=False)
    status = db.Column(db.Boolean, default=None, nullable=True)  # 审核状态：True=通过，False=拒绝，None=待审核
    reason = db.Column(db.String(150), nullable=False)  
    time = db.Column(db.DateTime, default=db.func.current_timestamp())

    permissions = ["vip", "admin", "api"]

    @classmethod
    def push_apply(cls, username, permission, reason, time=None):
        if permission not in cls.permissions:
            return False, "权限不存在"

        existing_apply = cls.query.filter_by(username=username, permission=permission).first()
        if existing_apply:
            return False, "您已经申请过该权限"

        # 处理 time 参数，支持字符串或 datetime 对象
        if time and isinstance(time, str):
            try:
                time = datetime.strptime(time, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return False, "时间格式错误，正确格式：YYYY-MM-DD HH:MM:SS"
        elif not time:
            time = datetime.now().replace(microsecond=0)

        new_apply = cls(username=username, permission=permission, reason=reason, time=time)
        db.session.add(new_apply)
        db.session.commit()
        return True, "申请成功，等待管理员审核"

    @classmethod
    def change_apply(cls, username, permission, status, need_entry=True):
        # 统一状态转换
        if isinstance(status, str):
            if status == "True":
                status = True
            elif status == "False":
                status = False
            else:
                return False, "状态无效"

        if permission not in cls.permissions:
            return False, "权限不存在"

        if need_entry == True:
            apply_entry = cls.query.filter_by(username=username, permission=permission).first()
            if (not apply_entry):
                return False, "申请记录不存在"

            apply_entry.status = status

        user = User.query.filter_by(username=username).first()
        if not user:
            return False, "用户不存在"

        if permission == "vip":
            user.vip = status
        elif permission == "admin":
            user.admin = status
        elif permission == "api":
            if status:
                user.api_token = str(uuid4())
            else:
                user.api_token = None

        db.session.commit()
        return True, "申请状态已更新", status


def initialize_system(app):
    """
    初始化系统数据库和Redis
    
    Args:
        app: Flask应用实例
    """
    with app.app_context():
        db.create_all()
        ensure_user_apply_columns(app)  # 确保数据表有新增字段

        redis_store = current_app.config.get('SESSION_REDIS')
        if redis_store:
            redis_store.flushdb()  # 注意：清空当前数据库，谨慎调用
            print("Redis 数据库已清空。")
        else:
            print("未配置 SESSION_REDIS，跳过清空 Redis 操作。")

    print("数据库和 Redis 初始化完成。")


def ensure_user_apply_columns(app):
    """
    确保用户申请表包含所有必要的列
    
    Args:
        app: Flask应用实例
    """
    with app.app_context():
        inspector = db.inspect(db.engine.get_bind(bind='apply_db'))
        columns = [col['name'] for col in inspector.get_columns('user_apply')]
        
        if 'status' not in columns:
            db.session.execute('ALTER TABLE user_apply ADD COLUMN status BOOLEAN DEFAULT NULL')
            db.session.commit()