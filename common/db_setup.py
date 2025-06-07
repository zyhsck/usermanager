"""
数据库设置和迁移管理模块

这个模块负责：
- 初始化SQLAlchemy
- 设置数据库连接
- 管理数据库迁移
"""

from flask_migrate import Migrate
import logging
from pathlib import Path
from .db_instance import db  # 使用相对导入
from models import UserData  # 从根目录导入UserData模型

# 确保模型被导入
__all__ = ['UserData']

# 初始化迁移
migrate = Migrate()

def init_db(app):
    """
    初始化数据库连接和配置
    
    Args:
        app: Flask应用实例
    """
    try:
        # 确保instance目录存在
        Path(app.instance_path).mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        db.init_app(app)
        
        # 初始化迁移
        migrate.init_app(app, db, directory='migrations')
        
        # 在应用上下文中创建所有表
        with app.app_context():
            db.create_all()
            
        logging.info("数据库初始化成功")
        
    except Exception as e:
        logging.error(f"数据库初始化失败: {e}")
        raise

def run_migrations(app):
    """
    运行所有待处理的数据库迁移
    
    Args:
        app: Flask应用实例
    """
    try:
        with app.app_context():
            migrate.upgrade()
        logging.info("数据库迁移完成")
        
    except Exception as e:
        logging.error(f"数据库迁移失败: {e}")
        raise