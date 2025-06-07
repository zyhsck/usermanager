import os
from datetime import timedelta

class BaseConfig:
    """基础配置类"""
    
    # 基本配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'zyh123456')
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    # 模板和静态文件路径
    TEMPLATE_FOLDER = os.path.join(BASE_DIR, 'templates')
    STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
    
    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(STATIC_FOLDER, 'uploads')
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Session配置
    SESSION_TYPE = 'redis'
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Redis配置
    REDIS_HOST = os.getenv('REDIS_HOST', '192.168.101.10')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 26739))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '123456')
    
    # 数据库配置
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'instance/user.db')
    SQLALCHEMY_BINDS = {
        'user_db': 'sqlite:///' + os.path.join(BASE_DIR, 'instance/user.db'),
        'apply_db': 'sqlite:///' + os.path.join(BASE_DIR, 'instance/apply.db'),
        'oauth_db': 'sqlite:///' + os.path.join(BASE_DIR, 'instance/oauth.db')
    }
    
    # 国际化配置
    BABEL_DEFAULT_LOCALE = 'zh'
    BABEL_SUPPORTED_LOCALES = ['en', 'zh']
    BABEL_TRANSLATION_DIRECTORIES = os.path.join(BASE_DIR, 'translations')
    
    # OAuth配置
    OAUTH_TOKEN_LENGTH = 32
    OAUTH_TOKEN_EXPIRES = timedelta(hours=1)
    OAUTH_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    LOG_FILE = os.path.join(BASE_DIR, 'logs/app.log')

class DevelopmentConfig(BaseConfig):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_ECHO = True
    
class TestingConfig(BaseConfig):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    
class ProductionConfig(BaseConfig):
    """生产环境配置"""
    DEBUG = False
    SQLALCHEMY_ECHO = False
    
    # 生产环境应该使用更安全的配置
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # 生产环境日志配置
    LOG_LEVEL = 'ERROR'

# 配置映射
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """获取当前环境的配置"""
    env = os.getenv('FLASK_ENV', 'default')
    return config[env]

# 工具函数
def ensure_directories():
    """确保必要的目录存在"""
    dirs = [
        os.path.join(BaseConfig.BASE_DIR, 'instance'),
        os.path.join(BaseConfig.BASE_DIR, 'logs'),
        BaseConfig.UPLOAD_FOLDER
    ]
    for directory in dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)

def init_app(app):
    """初始化应用配置"""
    config_class = get_config()
    app.config.from_object(config_class)
    
    # 确保必要的目录存在
    ensure_directories()
    
    # 设置日志
    import logging
    logging.basicConfig(
        filename=app.config['LOG_FILE'],
        level=getattr(logging, app.config['LOG_LEVEL']),
        format=app.config['LOG_FORMAT']
    )
    
    # 设置Redis会话
    from redis import Redis
    from flask_session import Session
    
    app.config['SESSION_REDIS'] = Redis(
        host=app.config['REDIS_HOST'],
        port=app.config['REDIS_PORT'],
        password=app.config['REDIS_PASSWORD']
    )
    Session(app)
    
    # 设置多语言支持
    from flask_babel import Babel
    
    def get_locale():
        from flask import request
        return request.cookies.get('lang', app.config['BABEL_DEFAULT_LOCALE'])
    
    babel = Babel(app, locale_selector=get_locale)
    
    return app