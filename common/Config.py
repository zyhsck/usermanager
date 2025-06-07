"""
配置管理模块

此模块提供了应用程序配置管理功能，包括：
- 基础配置类
- 环境特定配置类
- 配置初始化函数
- 服务器配置管理
"""

import os
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()
import json
import logging
from datetime import timedelta
from typing import Dict, Any, Optional, Union
import redis

# 基础配置类
class Config:
    """基础配置类，包含所有环境共享的配置"""
    
    # 应用基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev_key_please_change_in_production'
    SERVER_NAME_DISPLAY = 'User Management System'
    ALLOW_REGISTRATION = True
    MAX_USERS = 1000
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    LOG_LEVEL = 'INFO'
    MAINTENANCE_MODE = False
    MAINTENANCE_MESSAGE = ''
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = 'sqlite:///user_management.db'
    SQLALCHEMY_BINDS = {
        'user_db': 'sqlite:///user.db',
        'oauth_db': 'sqlite:///oauth.db',
        'apply_db': 'sqlite:///apply.db'
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Redis配置
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', '') or "123456"
    REDIS_URL = os.environ.get('REDIS_URL') or (
        f'redis://:{REDIS_PASSWORD}@192.168.101.10:26739/0' if REDIS_PASSWORD 
        else 'redis://192.168.101.10:26739/0'
    )
    
    # 会话配置
    SESSION_TYPE = 'redis'
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'user_management:'
    
    # OAuth配置
    OAUTH_TOKEN_EXPIRES = timedelta(hours=1)
    OAUTH_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # 邮件配置
    MAIL_SERVER = ''
    MAIL_PORT = 587
    MAIL_USERNAME = ''
    MAIL_PASSWORD = ''
    MAIL_USE_TLS = True
    MAIL_DEFAULT_SENDER = ''
    MAIL_ENABLED = False
    
    @staticmethod
    def update_app_config(debug=None, secret_key=None, session_lifetime=None):
        """更新应用配置
        
        Args:
            debug: 是否启用调试模式
            secret_key: 应用密钥
            session_lifetime: 会话生命周期(秒)
        """
        if debug is not None:
            Config.DEBUG = debug
        if secret_key is not None and secret_key:
            Config.SECRET_KEY = secret_key
        if session_lifetime is not None:
            Config.PERMANENT_SESSION_LIFETIME = timedelta(seconds=session_lifetime)
        
        # 保存到配置文件
        config_data = load_server_config()
        config_data['app_settings'] = {
            'debug': Config.DEBUG,
            'secret_key': Config.SECRET_KEY,
            'session_timeout': Config.PERMANENT_SESSION_LIFETIME.total_seconds()
        }
        save_server_config(config_data)

    @staticmethod
    def update_db_config(db_url=None, db_pool_size=None):
        """更新数据库配置
        
        Args:
            db_url: 数据库连接URL
            db_pool_size: 连接池大小
        """
        if db_url is not None and db_url:
            Config.SQLALCHEMY_DATABASE_URI = db_url
        if db_pool_size is not None:
            Config.SQLALCHEMY_POOL_SIZE = db_pool_size
        
        # 保存到配置文件
        config_data = load_server_config()
        config_data['database_settings'] = {
            'db_url': Config.SQLALCHEMY_DATABASE_URI,
            'pool_size': getattr(Config, 'SQLALCHEMY_POOL_SIZE', None)
        }
        save_server_config(config_data)

    @staticmethod
    def update_smtp_config(server=None, port=None, username=None, password=None, 
                         use_tls=None, from_email=None, enabled=None):
        """更新SMTP邮件配置
        
        Args:
            server: SMTP服务器地址
            port: SMTP端口
            username: SMTP用户名
            password: SMTP密码
            use_tls: 是否使用TLS
            from_email: 默认发件人
            enabled: 是否启用邮件功能
        """
        if server is not None:
            Config.MAIL_SERVER = server
        if port is not None:
            Config.MAIL_PORT = port
        if username is not None:
            Config.MAIL_USERNAME = username
        if password is not None and password != '********':
            Config.MAIL_PASSWORD = password
        if use_tls is not None:
            Config.MAIL_USE_TLS = use_tls
        if from_email is not None:
            Config.MAIL_DEFAULT_SENDER = from_email
        if enabled is not None:
            Config.MAIL_ENABLED = enabled
        
        # 保存到配置文件
        config_data = load_server_config()
        config_data['smtp_settings'] = {
            'server': Config.MAIL_SERVER,
            'port': Config.MAIL_PORT,
            'username': Config.MAIL_USERNAME,
            'use_tls': Config.MAIL_USE_TLS,
            'from_email': Config.MAIL_DEFAULT_SENDER,
            'enabled': Config.MAIL_ENABLED
        }
        save_server_config(config_data)

    @staticmethod
    def update_redis_config(url=None, password=None):
        """更新Redis配置
        
        Args:
            url: Redis连接URL
            password: Redis密码
        """
        if url is not None and url:
            Config.REDIS_URL = url
        if password is not None and password != '********':
            Config.REDIS_PASSWORD = password
            Config.REDIS_URL = f'redis://:{password}@192.168.101.10:26739/0'
        
        # 保存到配置文件
        config_data = load_server_config()
        config_data['redis_settings'] = {
            'url': Config.REDIS_URL,
            'password': '********'  # 不保存明文密码
        }
        save_server_config(config_data)

    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        # 设置日志级别
        app.logger.setLevel(getattr(logging, app.config.get('LOG_LEVEL', 'INFO')))
        
        # 初始化Redis连接
        redis_url = app.config.get('REDIS_URL')
        if redis_url:
            app.config['SESSION_REDIS'] = redis.from_url(redis_url)
        
        # 加载服务器配置
        try:
            server_config = load_server_config()
            if server_config:
                # 更新应用配置
                app.config.update({
                    'SERVER_NAME_DISPLAY': server_config.get('server_name', app.config.get('SERVER_NAME_DISPLAY')),
                    'ALLOW_REGISTRATION': server_config.get('allow_registration', app.config.get('ALLOW_REGISTRATION')),
                    'MAX_USERS': server_config.get('max_users', app.config.get('MAX_USERS')),
                    'PERMANENT_SESSION_LIFETIME': timedelta(seconds=server_config.get('session_timeout', 86400)),
                    'LOG_LEVEL': server_config.get('log_level', app.config.get('LOG_LEVEL')).upper(),
                    'MAINTENANCE_MODE': server_config.get('maintenance_mode', app.config.get('MAINTENANCE_MODE')),
                    'MAINTENANCE_MESSAGE': server_config.get('maintenance_message', app.config.get('MAINTENANCE_MESSAGE'))
                })
                
                # 更新邮件配置
                smtp_settings = server_config.get('smtp_settings', {})
                if smtp_settings:
                    app.config.update({
                        'MAIL_SERVER': smtp_settings.get('server', app.config.get('MAIL_SERVER')),
                        'MAIL_PORT': smtp_settings.get('port', app.config.get('MAIL_PORT')),
                        'MAIL_USERNAME': smtp_settings.get('username', app.config.get('MAIL_USERNAME')),
                        'MAIL_USE_TLS': smtp_settings.get('use_tls', app.config.get('MAIL_USE_TLS')),
                        'MAIL_DEFAULT_SENDER': smtp_settings.get('from_email', app.config.get('MAIL_DEFAULT_SENDER')),
                        'MAIL_ENABLED': smtp_settings.get('enabled', app.config.get('MAIL_ENABLED'))
                    })
                    
                    # 只有当配置中有密码时才更新密码
                    if 'password' in smtp_settings:
                        app.config['MAIL_PASSWORD'] = smtp_settings['password']
        except Exception as e:
            logging.error(f"加载服务器配置失败: {e}")


# 开发环境配置
class DevelopmentConfig(Config):
    """开发环境特定配置"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///user_management_dev.db'


# 测试环境配置
class TestingConfig(Config):
    """测试环境特定配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


# 生产环境配置
class ProductionConfig(Config):
    """生产环境特定配置"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///user_management_prod.db'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'production_key_please_change'
    
    @classmethod
    def init_app(cls, app):
        """生产环境特定的初始化"""
        Config.init_app(app)
        
        # 在生产环境中配置日志到文件
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        file_handler = logging.FileHandler('logs/user_management.log')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        app.logger.addHandler(file_handler)


# 配置映射
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


# 服务器配置文件路径
SERVER_CONFIG_FILE = 'server_config.json'


def load_server_config() -> Dict[str, Any]:
    """
    从配置文件加载服务器配置
    
    Returns:
        Dict[str, Any]: 服务器配置字典
    """
    try:
        if os.path.exists(SERVER_CONFIG_FILE):
            with open(SERVER_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"加载服务器配置文件失败: {e}")
    
    return {}


def save_server_config(config_data: Dict[str, Any]) -> bool:
    """
    保存服务器配置到文件
    
    Args:
        config_data (Dict[str, Any]): 要保存的配置数据
        
    Returns:
        bool: 保存是否成功
    """
    try:
        with open(SERVER_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"保存服务器配置文件失败: {e}")
        return False


# 导出配置实例
config_instance = config[os.getenv('FLASK_ENV', 'default')]


def get_config():
    """
    获取当前配置实例
    
    Returns:
        Config: 当前环境配置实例
    """
    return config_instance


# 初始化应用配置
def init_app(app):
    """
    初始化Flask应用的配置
    
    Args:
        app: Flask应用实例
    """
    # 从环境变量获取配置类型
    config_name = os.getenv('FLASK_ENV', 'default')
    
    # 加载配置
    app.config.from_object(config[config_name])
    
    # 调用配置类的初始化方法
    config[config_name].init_app(app)
    
    # 设置会话永久
    app.permanent_session_lifetime = app.config.get('PERMANENT_SESSION_LIFETIME')